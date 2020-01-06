import json
import os
import random
from base64 import b64decode

from anydex.core.community import MarketCommunity
from anydex.core.assetamount import AssetAmount
from anydex.core.assetpair import AssetPair
from anydex.core.message import TraderId
from anydex.wallet.dummy_wallet import DummyWallet1, DummyWallet2
from anydex.wallet.tc_wallet import TrustchainWallet

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module

from ipv8.peer import Peer


@static_module
class MarketModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the market community.
    """

    def __init__(self, experiment):
        super(MarketModule, self).__init__(experiment, MarketCommunity)
        self.num_bids = 0
        self.num_asks = 0
        self.order_id_map = {}

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    @experiment_callback
    def init_wallets(self):
        dummy1_wallet = DummyWallet1()
        dummy2_wallet = DummyWallet2()
        self.overlay.use_local_address = True
        self.overlay.wallets = {
            dummy1_wallet.get_identifier(): dummy1_wallet,
            dummy2_wallet.get_identifier(): dummy2_wallet
        }

        dummy1_wallet.balance = 1000000000
        dummy2_wallet.balance = 1000000000
        dummy1_wallet.MONITOR_DELAY = 0
        dummy2_wallet.MONITOR_DELAY = 0

        tc_wallet = TrustchainWallet(self.session.trustchain_community)
        tc_wallet.check_negative_balance = False
        self.overlay.wallets[tc_wallet.get_identifier()] = tc_wallet

    @experiment_callback
    def init_matchmakers(self):
        peer_num = self.experiment.scenario_runner._peernumber
        if peer_num > int(os.environ['NUM_MATCHMAKERS']):
            self.overlay.disable_matchmaker()

    @experiment_callback
    def disable_max_peers(self):
        self.overlay.max_peers = -1

    @experiment_callback
    def connect_matchmakers(self, num_to_connect):
        num_total_matchmakers = int(os.environ['NUM_MATCHMAKERS'])
        if int(num_to_connect) > num_total_matchmakers:
            connect = range(1, num_total_matchmakers + 1)
        else:
            connect = random.sample(range(1, num_total_matchmakers + 1), int(num_to_connect))

        # Send introduction request to matchmakers
        for peer_num in connect:
            self._logger.info("Connecting to matchmaker %d", peer_num)
            self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_num))

    @experiment_callback
    def init_trader_lookup_table(self):
        """
        Initialize the lookup table for all traders so we do not have to use the DHT.
        """
        num_total_matchmakers = int(os.environ['NUM_MATCHMAKERS'])
        for peer_id in self.all_vars.keys():
            target = self.all_vars[peer_id]
            address = (str(target['host']), target['port'])

            if 'public_key' not in self.all_vars[peer_id]:
                self._logger.error("Could not find public key of peer %s!", peer_id)
            else:
                peer = Peer(b64decode(self.all_vars[peer_id]['public_key']), address=address)
                self.overlay.update_ip(TraderId(peer.mid), address)

                if int(peer_id) <= num_total_matchmakers:
                    self.overlay.matchmakers.add(peer)

    @experiment_callback
    def ask(self, asset1_amount, asset1_type, asset2_amount, asset2_type, order_id=None):
        self.num_asks += 1
        pair = AssetPair(AssetAmount(int(asset1_amount), asset1_type), AssetAmount(int(asset2_amount), asset2_type))
        order = self.overlay.create_ask(pair, 3600)
        if order_id:
            self.order_id_map[order_id] = order.order_id

    @experiment_callback
    def bid(self, asset1_amount, asset1_type, asset2_amount, asset2_type, order_id=None):
        self.num_bids += 1
        pair = AssetPair(AssetAmount(int(asset1_amount), asset1_type), AssetAmount(int(asset2_amount), asset2_type))
        order = self.overlay.create_bid(pair, 3600)
        if order_id:
            self.order_id_map[order_id] = order.order_id

    @experiment_callback
    def cancel(self, order_id):
        if order_id not in self.order_id_map:
            self._logger.warning("Want to cancel order but order id %s not found!", order_id)
            return

        self.overlay.cancel_order(self.order_id_map[order_id])

    @experiment_callback
    def write_stats(self):
        scenario_runner = self.experiment.scenario_runner
        transactions = []

        # Parse transactions
        for transaction in self.overlay.transaction_manager.find_all():
            partner_peer_id = self.overlay.lookup_ip(transaction.partner_order_id.trader_id)[1] - 12000
            if partner_peer_id < scenario_runner._peernumber:  # Only one peer writes the transaction
                transactions.append((int(transaction.timestamp) / 1000.0 - scenario_runner.exp_start_time,
                                     transaction.transferred_assets.first.amount,
                                     transaction.transferred_assets.second.amount,
                                     len(transaction.payments), scenario_runner._peernumber, partner_peer_id))

        # Write transactions
        with open('transactions.log', 'w') as transactions_file:
            for transaction in transactions:
                transactions_file.write("%s,%s,%s,%s,%s,%s\n" % transaction)

        # Write orders
        with open('orders.log', 'w') as orders_file:
            for order in self.overlay.order_manager.order_repository.find_all():
                order_data = (int(order.timestamp) / 1000.0, order.order_id, scenario_runner._peernumber,
                              'ask' if order.is_ask() else 'bid',
                              'complete' if order.is_complete() else 'incomplete',
                              order.assets.first.amount, order.assets.second.amount, order.reserved_quantity,
                              order.traded_quantity,
                              (int(order.completed_timestamp) / 1000.0) if order.is_complete() else '-1')
                orders_file.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % order_data)

        # Write ticks in order book
        with open('orderbook.txt', 'w') as orderbook_file:
            orderbook_file.write(str(self.overlay.order_book))

        # Write known matchmakers
        with open('matchmakers.txt', 'w') as matchmakers_file:
            for matchmaker in self.overlay.matchmakers:
                matchmakers_file.write("%s,%d\n" % (matchmaker.address[0], matchmaker.address[1]))

        # Get statistics about the amount of fulfilled orders (asks/bids)
        fulfilled_asks = 0
        fulfilled_bids = 0
        for order in self.overlay.order_manager.order_repository.find_all():
            if order.is_complete():  # order is fulfilled
                if order.is_ask():
                    fulfilled_asks += 1
                else:
                    fulfilled_bids += 1

        with open('market_stats.log', 'w') as stats_file:
            stats_dict = {'asks': self.num_asks, 'bids': self.num_bids,
                          'fulfilled_asks': fulfilled_asks, 'fulfilled_bids': fulfilled_bids}
            stats_file.write(json.dumps(stats_dict))

        # Write mid register
        with open('mid_register.log', 'w') as mid_file:
            for trader_id, host in self.overlay.mid_register.items():
                mid_file.write("%s,%s\n" % (trader_id.as_hex(), "%s:%d" % host))

        # Write items in the matching queue
        with open('match_queue.txt', 'w') as queue_file:
            for match_cache in self.overlay.get_match_caches():
                for retries, price, other_order_id in match_cache.queue.queue:
                    queue_file.write(
                        "%s,%d,%s,%s\n" % (match_cache.order.order_id, retries, price, other_order_id))
