import csv
import json
import os
import time
from binascii import hexlify
from random import randint, random, choice

import networkx as nx
from twisted.internet import reactor
from twisted.internet.task import LoopingCall, deferLater

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module
from ipv8.attestation.trustchain.community import TrustChainCommunity
from ipv8.attestation.trustchain.listener import BlockListener
from ipv8.attestation.trustchain.settings import SecurityMode


class FakeBlockListener(BlockListener):
    """
    Block listener that only signs blocks
    """

    def should_sign(self, _):
        return True

    def received_block(self, block):
        pass


class GeneratedBlockListener(BlockListener):
    """
    This block listener to measure throughput.
    This peer will not sign blocks
    """

    def __init__(self, mes_file):
        # File to safe measurements
        self.file_name = mes_file
        self.start_time = None

    def should_sign(self, _):
        return True

    def received_block(self, block):
        # Add block to stat file
        pass


@static_module
class TrustchainModule(IPv8OverlayExperimentModule):
    def __init__(self, experiment):
        super(TrustchainModule, self).__init__(experiment, TrustChainCommunity)
        self.request_signatures_lc = None
        self.num_blocks_in_db_lc = None
        self.block_stat_file = None
        self.request_ds_lc = None
        self.did_write_start_time = False
        self.tx_lc = None

        if os.getenv('TX_RATE'):
            self.tx_rate = int(os.getenv('TX_RATE'))
        else:
            self.tx_rate = 64

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    @experiment_callback
    def init_trustchain_settings(self):
        self._logger.info("Setting id to %s", self.my_id)
        self.overlay.settings.my_id = self.my_id
        if os.getenv('TTL'):
            self.set_ttl(os.getenv('TTL'))
        if os.getenv('FANOUT'):
            self.set_fanout(os.getenv('FANOUT'))
        if os.getenv('SYNC_TIME'):
            self.set_sync_time(os.getenv('SYNC_TIME'))
        if os.getenv('NUM_WIT'):
            self.overlay.settings.com_size = int(os.getenv('NUM_WIT'))
        if os.getenv('AUDIT_ON'):
            self.overlay.settings.security_mode = SecurityMode.AUDIT
        if os.getenv('RISK'):
            self.overlay.settings.risk = float(os.getenv('RISK'))

    @experiment_callback
    def turn_off_broadcast(self):
        self.overlay.settings.broadcast_blocks = False

    @experiment_callback
    def turn_off_validation(self):
        self.overlay.settings.ignore_validation = True

    @experiment_callback
    def hide_blocks(self):
        self.overlay.settings.is_hiding = True

    @experiment_callback
    def set_sync_time(self, value):
        self.overlay.settings.sync_time = float(value)
        self._logger.info("Setting sync time to %s", value)

    @experiment_callback
    def set_ttl(self, value):
        self.overlay.settings.ttl = int(value)
        self._logger.info("Setting ttl for broadcast to %s", value)

    @experiment_callback
    def set_fanout(self, value):
        self.overlay.settings.broadcast_fanout = int(value)
        self._logger.info("Setting broadcast to %s", value)

    @experiment_callback
    def turn_informed_broadcast(self):
        self.overlay.settings.use_informed_broadcast = True

    @experiment_callback
    def init_block_writer(self):
        # Open projects output directory and save blocks arrival time
        self.block_stat_file = 'blocks.csv'
        with open(self.block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', 'type', "seq_num", "link", 'from_id', 'to_id'])
            writer.writeheader()
        self.overlay.persistence.block_file = self.block_stat_file
        self.overlay.add_listener(GeneratedBlockListener(self.block_stat_file), [b'claim', b'spend', b'test'])

    @experiment_callback
    def init_trustchain(self):
        self.overlay.add_listener(FakeBlockListener(), [b'test'])

    @experiment_callback
    def disable_max_peers(self):
        self.overlay.max_peers = -1

    @experiment_callback
    def enable_trustchain_memory_db(self):
        self.tribler_config.set_trustchain_memory_db(True)

    @experiment_callback
    def enable_trustchain_pex(self):
        self.tribler_config.set_pex_discovery(True)

    @experiment_callback
    def set_validation_range(self, value):

        if os.getenv('VALID_WINDOW'):
            value = int(os.getenv('VALID_WINDOW'))

        self._logger.info("Setting validation range to %s", value)

        self.overlay.settings.validation_range = int(value)

    @experiment_callback
    def enable_crawler(self):
        self.overlay.settings.crawler = True

    @experiment_callback
    def start_requesting_signatures(self):

        if os.getenv('TX_SEC'):
            value = float(os.getenv('TX_SEC'))
        else:
            value = 0.001
        self._logger.info("Setting transaction rate to %s", 1 / value)

        self.request_signatures_lc = LoopingCall(self.request_random_signature)
        self.request_signatures_lc.start(value)

    @experiment_callback
    def start_periodic_mem_flush(self):
        value = 1
        if os.getenv('FLUSH_TIME'):
            value = float(os.getenv('FLUSH_TIME'))

        self.overlay.init_mem_db_flush(value)

    @experiment_callback
    def start_multihop_noodle_transactions(self):
        if os.getenv('TX_SEC'):
            value = float(os.getenv('TX_SEC'))
        else:
            value = 0.001

        self.request_signatures_lc = LoopingCall(self.request_noodle_all_random_signature)
        self.request_signatures_lc.start(value)

    def is_minter(self):
        """
        Return whether you are a minter or not.
        """
        num_minters = 1
        if os.getenv('NUM_MINTERS'):
            num_minters = int(os.getenv('NUM_MINTERS'))

        num_nodes = len(self.all_vars.keys())
        num_minters = min(num_nodes, num_minters)

        return self.my_id <= num_minters

    @experiment_callback
    def mint(self):
        """
        Have minters mint some initial value.
        """
        if not self.is_minter():
            return

        self._logger.info("Minting initial value...")
        mint = self.overlay.prepare_mint_transaction()
        self.overlay.self_sign_block(block_type=b'claim', transaction=mint)

    @experiment_callback
    def minter_send_to_all(self):
        """
        Have the minter send initial value to all known peers.
        """
        if not self.is_minter():
            return

        self._logger.info("Sending initial value to all peers...")

        peers = self.overlay.get_all_communities_peers()
        for peer in peers:
            delay = (1.0 / len(peers)) * int(self.experiment.get_peer_id(peer.address[0], peer.address[1]))
            deferLater(reactor, delay, self.transfer, peer, 1000)

    @experiment_callback
    def start_creating_transactions(self):
        if not self.did_write_start_time:
            # Write the start time to a file
            submit_tx_start_time = int(round(time.time() * 1000))
            with open("submit_tx_start_time.txt", "w") as out_file:
                out_file.write("%d" % submit_tx_start_time)
            self.did_write_start_time = True

        self._logger.info("Starting transactions...")
        total_peers = len(self.all_vars.keys())
        self.tx_lc = LoopingCall(self.request_noodle_community_signature)

        # Depending on the tx rate and number of clients, wait a bit
        individual_tx_rate = int(self.tx_rate) / total_peers
        self._logger.info("Individual tx rate: %f" % individual_tx_rate)

        def start_lc():
            self._logger.info("Starting tx lc...")
            self.tx_lc.start(1.0 / individual_tx_rate)

        my_peer_id = self.experiment.scenario_runner._peernumber
        deferLater(reactor, (1.0 / total_peers) * (my_peer_id - 1), start_lc)

    @experiment_callback
    def stop_creating_transactions(self):
        self._logger.info("Stopping transactions...")
        self.tx_lc.stop()
        self.tx_lc = None

    @experiment_callback
    def start_direct_noodle_transactions(self):
        if os.getenv('TX_SEC'):
            value = float(os.getenv('TX_SEC'))
        else:
            value = 0.001

        self.request_signatures_lc = LoopingCall(self.request_noodle_1hop_random_signature)
        self.request_signatures_lc.start(value)

        # def start_sig_req():

        # sleep_offset = (self.my_id-1)/len(self.all_vars)
        # self.overlay.register_anonymous_task("init_delay", reactor.callLater(sleep_offset, start_sig_req))

    @experiment_callback
    def stop_requesting_signatures(self):
        self.request_signatures_lc.stop()
        self.overlay.all_sync_stop()

    @experiment_callback
    def start_req_sign_with_random_double_spends(self, batch=1, chance=0.1):

        if os.getenv('DS_BATCH'):
            batch = int(os.getenv('DS_BATCH'))
        if os.getenv('DS_CHANCE'):
            chance = float(os.getenv('DS_CHANCE'))

        self._logger.info("Double spend batch is %s", batch)
        self._logger.info("Double spend chance is %s", chance)
        self.request_ds_lc = LoopingCall(self.make_double_spend, batch, chance)
        self.request_ds_lc.start(1)

    @experiment_callback
    def stop_req_sign_with_random_double_spends(self):
        self.request_ds_lc.stop()

    @experiment_callback
    def start_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_lc = LoopingCall(self.check_num_blocks_in_db)
        self.num_blocks_in_db_lc.start(1)

    @experiment_callback
    def stop_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_lc.stop()

    @experiment_callback
    def request_signature(self, peer_id, up, down):
        self.request_signature_from_peer(self.get_peer(peer_id), up, down)

    @experiment_callback
    def request_crawl(self, peer_id, sequence_number):
        self._logger.info("%s: Requesting block: %s for peer: %s" % (self.my_id, sequence_number, peer_id))
        self.overlay.send_crawl_request(self.get_peer(peer_id),
                                        self.get_peer(peer_id).public_key.key_to_bin(),
                                        int(sequence_number))

    @experiment_callback
    def request_noodle_1hop_random_signature(self):
        """
        Request a random signature from one of your known verified peers
        """
        self.transfer(choice(list(self.overlay.get_peers())), random())

    def request_noodle_community_signature(self):
        """
        Request signature from peer that is either directly connected or is part of my community.
        """
        minters = set(self.overlay.get_peers())
        peers = self.overlay.get_all_communities_peers()
        peers.update(minters)
        self.transfer(choice(list(peers)), 1)

    @experiment_callback
    def request_noodle_all_random_signature(self):
        """
        Request a random signature from one of your known verified peers
        """
        # choose a random peer in the overlay, except yourself

        eligible_peers = set(self.experiment.get_peers()) - {str(self.my_id)}
        peer_id = choice(list(eligible_peers))
        self.transfer(self.get_peer(peer_id), random())

    @experiment_callback
    def request_random_signature(self, attach_to_block=None):
        """
        Request a random signature from one of your known verified peers
        """
        rand_up = randint(1, 1000)
        rand_down = randint(1, 1000)

        if not self.overlay.network.verified_peers:
            self._logger.warning("No verified peers to request random signature from!")
            return

        self.request_signature_from_peer(choice(list(self.overlay.get_peers())),
                                         rand_up * 1024 * 1024, rand_down * 1024 * 1024,
                                         attached_block=attach_to_block)

    @experiment_callback
    def make_double_spend(self, num_ds=1, chance=0.3):
        blk = self.overlay.persistence.get_latest(self.overlay.my_peer.public_key.key_to_bin())
        if not blk:
            self._logger.error("Cannot find last block of own peer")
            self.request_random_signature()
        else:
            if random() < chance:
                self._logger.warn("Creating a double spend block %s", blk.sequence_number - 1)
                for _ in range(num_ds):
                    self.request_random_signature(blk.sequence_number - 1)
            else:
                self.request_random_signature()

    def send_to_leader_peer(self, block_num):
        leader_peer = self.overlay.network.verified_peers[0]
        for _ in range(block_num):
            rand_up = randint(1, 1000)
            rand_down = randint(1, 1000)
            self.request_signature_from_peer(leader_peer, rand_up, rand_down)

    @experiment_callback
    def start_spamming_leader_peer(self, block_num=100):
        """
        Send block_num of blocks per second to leader peer per second.
        NUM_TX environment variable will be used instead of block_num if defined
        :param block_num: number of blocks per sec to send to leader peer
        """
        if os.getenv('NUM_TX'):
            block_num = int(os.getenv('NUM_TX'))

        self.request_signatures_lc = LoopingCall(self.send_to_leader_peer, int(block_num))
        self.request_signatures_lc.start(1)

    def request_signature_from_peer(self, peer, up, down, attached_block=None):
        peer_id = self.experiment.get_peer_id(peer.address[0], peer.address[1])
        self._logger.info("%s: Requesting signature from peer: %s", self.my_id, peer_id)
        transaction = {"up": up, "down": down, "from_peer": self.my_id, "to_peer": peer_id}
        self.overlay.sign_block(peer, peer.public_key.key_to_bin(),
                                block_type=b'test', transaction=transaction,
                                double_spend_block=attached_block)

    def transfer(self, peer, spend_value):

        dest_peer_id = self.experiment.get_peer_id(peer.address[0], peer.address[1])
        self._logger.debug("Making spend to peer %s (value: %f)", dest_peer_id, spend_value)

        val = self.overlay.prepare_spend_transaction(peer.public_key.key_to_bin(), spend_value)
        if not val:
            self._logger.warning("No tokens to spend. Waiting for tokens")
            return

        next_hop_peer, tx = val
        next_hop_peer_id = self.experiment.get_peer_id(next_hop_peer.address[0], next_hop_peer.address[1])
        if next_hop_peer_id != dest_peer_id:
            # Multi-hop payment, add condition + nonce
            nonce = self.overlay.persistence.get_new_peer_nonce(peer.public_key.key_to_bin())
            condition = hexlify(peer.public_key.key_to_bin()).decode()
            tx.update({'nonce': nonce, 'condition': condition})
        self.overlay.sign_block(next_hop_peer, next_hop_peer.public_key.key_to_bin(),
                                block_type=b'spend', transaction=tx)

    def check_num_blocks_in_db(self):
        """
        Check the total number of blocks we have in the database and write it to a file.
        """
        num_blocks = len(self.overlay.persistence.get_all_blocks())
        with open('num_trustchain_blocks.txt', 'a') as output_file:
            elapsed_time = time.time() - self.experiment.scenario_runner.exp_start_time
            output_file.write("%f,%d\n" % (elapsed_time, num_blocks))

    @experiment_callback
    def commit_blocks_to_db(self):
        if self.session.config.use_trustchain_memory_db():
            self.overlay.persistence.commit(self.overlay.my_peer.public_key.key_to_bin())

    @experiment_callback
    def commit_block_times(self):
        self._logger.error("Commit block times to the file %s", self.overlay.persistence.block_file)
        if self.session.config.use_trustchain_memory_db():
            self._logger.error("Commit block times to the file %s", self.overlay.persistence.block_file)
            self.overlay.persistence.commit_block_times()

    @experiment_callback
    def write_trustchain_statistics(self):
        from anydex.wallet.tc_wallet import TrustchainWallet
        with open('trustchain.txt', 'w') as trustchain_file:
            wallet = TrustchainWallet(self.overlay)
            trustchain_file.write(json.dumps(wallet.get_statistics()))
