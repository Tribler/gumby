import json
import os
import random
import shutil
import subprocess
from asyncio import get_event_loop

import time
from threading import Thread

from grapheneapi.grapheneapi import GrapheneAPI

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import static_module, ExperimentModule
from gumby.util import run_task


@static_module
class BitsharesModule(BlockchainModule):

    def __init__(self, experiment):
        super().__init__(experiment)
        self.wallet_rpc = None
        self.wallet_rpc_user = None
        self.wallet_rpc_password = "supersecret"
        self.brain_priv_key = None
        self.wif_priv_key = None
        self.pub_key = None
        self.trade_lc = None
        self.username = None
        self.bs_process = None
        self.wallet_process = None
        self.create_ask = True
        self.orders_info = []  # Keeps track of tuples: (order_creation_time, signature)
        self.tx_info = []
        self.devnet_dir = "/tmp/bitshares"

        self.order_id_map = {}
        self.cancelled_orders = set()
        self.dump_blockchain_lc = None
        self.last_block_written = 0
        self.data_dir = None

    def on_all_vars_received(self):
        super().on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    def load_keys(self):
        account_number = self.my_id - 1

        if not self.username:
            self.username = "user%d" % account_number

        if not self.brain_priv_key:
            # Read the keys
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "keypairs.txt"), "r") as keys_file:
                lines = keys_file.readlines()
                for ind, line in enumerate(lines):
                    if len(line) > 0 and ind == account_number:
                        parts = line.rstrip('\n').split(",")
                        self.brain_priv_key = parts[0]
                        self.pub_key = parts[1]
                        self.wif_priv_key = parts[2]

    @experiment_callback
    def start_dumping_blockchain(self):
        if not self.dump_blockchain_lc:
            self.dump_blockchain_lc = run_task(self.dump_blockchain, interval=10)

    @experiment_callback
    def start_bitshares(self):
        if self.is_client():
            return

        # Reset and copy the data directory
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.copytree(os.path.join(self.devnet_dir, "data-clean-%d" % self.num_validators), self.data_dir)

        self.load_keys()

        # First, we create a configuration file out of the template configuration
        with open(os.path.join(self.devnet_dir, "config-template.ini"), "r") as template_conf_file:
            template_content = template_conf_file.read()

        self.wallet_rpc_user = "1.6.%d" % self.my_id
        print("Assigned peer id: %d" % self.my_id)
        template_content = template_content.replace("<BITSHARES_P2P_ENDPOINT>", "0.0.0.0:%d" % (11000 + self.my_id))
        if self.my_id != 1:
            peer_1 = self.experiment.get_peer_ip_port_by_id(1)
            template_content = template_content.replace("<BITSHARES_SEED_NODE>", 'seed-nodes = ["%s:11001"]'
                                                        % peer_1[0])
        else:
            template_content = template_content.replace("<BITSHARES_SEED_NODE>", "seed-nodes = []")
        template_content = template_content.replace("<BITSHARES_RPC_ENDPOINT>", "0.0.0.0:%d" % (12000 + self.my_id))
        template_content = template_content.replace("<BITSHARES_WITNESS_ID>", self.wallet_rpc_user)
        template_content = template_content.replace("<BITSHARES_PUBLIC_KEY>", self.pub_key)
        template_content = template_content.replace("<BITSHARES_PRIVATE_KEY>", self.wif_priv_key)

        with open(os.path.join(self.data_dir, "config.ini"), "w") as conf_file:
            conf_file.write(template_content)

        # Now we start the witness node
        if self.experiment.my_id == 1:
            self.start_bitshares_process()
        else:
            run_task(self.start_bitshares_process, delay=random.random() * 10)

    def on_id_received(self):
        super().on_id_received()
        self.data_dir = os.path.join("/tmp", "bitshares_data_%d" % self.my_id)
        self.create_ask = (self.my_id % 2 == 0)

    def start_bitshares_process(self):
        bitshares_exec = os.path.join(self.devnet_dir, "witness_node")
        genesis_path = os.path.join(self.devnet_dir, "genesis", "my-genesis.json")
        cmd = '%s --genesis-json=%s --data-dir %s --partial-operations true' % \
              (bitshares_exec, genesis_path, self.data_dir)
        bitshares_out_file = open("bitshares_output.log", "w")
        self.bs_process = subprocess.Popen(cmd.split(" "), stdout=bitshares_out_file)

    @experiment_callback
    def start_cli_wallet(self):
        if self.is_client():
            return

        server_rpc_port = 12000 + self.my_id
        wallet_rpc_port = 13000 + self.my_id

        # Get the chain ID
        with open(os.path.join(self.devnet_dir, "chainid-%d" % self.num_validators), "r") as chainid_file:
            chain_id = chainid_file.read().rstrip('\n')

        print("Starting CLI wallet with chain ID: %s" % chain_id)

        cli_wallet_exec = os.path.join(self.devnet_dir, "cli_wallet")
        cmd = '%s --wallet-file=my-wallet.json --chain-id %s --server-rpc-endpoint=ws://127.0.0.1:%d ' \
              '--server-rpc-user=%s --server-rpc-password=%s --rpc-endpoint=0.0.0.0:%d --daemon' \
              % (cli_wallet_exec, chain_id, server_rpc_port, self.wallet_rpc_user,
                 self.wallet_rpc_password, wallet_rpc_port)
        wallet_out_file = open("bitshares_wallet_output.log", "w")
        self.wallet_process = subprocess.Popen(cmd.split(" "), stdout=wallet_out_file)

    @experiment_callback
    def unlock_cli_wallet(self):
        if self.is_client():
            return  # Only validators themselves unlock wallets

        self._logger.info("Unlocking CLI wallet...")

        self._logger.info("Connecting to localhost wallet on port %d...", 13000 + self.my_id)
        self.wallet_rpc = GrapheneAPI("127.0.0.1", 13000 + self.my_id, "", "")
        self.wallet_rpc.set_password("secret")
        self.wallet_rpc.unlock("secret")

    @experiment_callback
    def import_wallet_key(self):
        if not self.is_client():
            return  # Only clients import their wallet keys

        self.load_keys()

        validator_peer_id = (self.my_id - 1) % self.num_validators
        validator_host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id + 1)
        validator_port = 13000 + validator_peer_id + 1

        self._logger.info("Connecting to wallet on host %s and port %d...", validator_host, validator_port)
        self.wallet_rpc = GrapheneAPI(validator_host, validator_port, "", "")

        self._logger.info("Import wallet key...")
        self.wallet_rpc.import_key(self.username, self.wif_priv_key)

    @experiment_callback
    def init_nathan(self):
        self.wallet_rpc.import_key("nathan", "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3")
        self.wallet_rpc.import_balance("nathan", ["5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"], True)

    @experiment_callback
    def transfer_asset_to_all_peers(self, asset_name):
        for peer_id in self.experiment.get_peers():
            response = self.wallet_rpc.transfer(
                "nathan", "user%d" % (int(peer_id) - 1), 100000, asset_name, "transferral", True)
            print("Transferred %s assets to peer %d, response: %s" % (asset_name, int(peer_id), response))

    def post_order(self, order_type, spend_asset_name, receive_asset_name, price, amount):
        if order_type == "bid":
            spend_asset_name, receive_asset_name = receive_asset_name, spend_asset_name

        print("New order: spending %s, receiving %s, price: %d, amount: %d (account: %s)"
              % (spend_asset_name, receive_asset_name, int(price), int(amount), self.username))

        order_creation_time = int(round(time.time() * 1000))
        response = self.wallet_rpc.sell_asset(self.username, int(price), spend_asset_name, int(amount),
                                              receive_asset_name, 3600, False, True)
        self.orders_info.append((order_creation_time, response["signatures"][0]))
        print("Placed order, response: %s" % response)

        return response

    @experiment_callback
    def ask(self, price, price_type, quantity, quantity_type, order_id=None):
        response = self.post_order('ask', price_type, quantity_type, price, quantity)

        if order_id and order_id not in self.cancelled_orders:
            self.order_id_map[order_id] = response

    @experiment_callback
    def bid(self, price, price_type, quantity, quantity_type, order_id=None):
        response = self.post_order('bid', price_type, quantity_type, price, quantity)

        if order_id and order_id not in self.cancelled_orders:
            self.order_id_map[order_id] = response

    def create_random_order(self):
        if self.create_ask:
            self.ask("10", "DUM1", "10", "DUM2")
        else:
            self.bid("10", "DUM1", "10", "DUM2")
        self.create_ask = not self.create_ask

    @experiment_callback
    def start_creating_orders(self):
        print("Starting with random orders at %s" % int(round(time.time() * 1000)))
        self.trade_lc.start(0.5)

    @experiment_callback
    def stop_creating_orders(self):
        self.trade_lc.cancel()

    @experiment_callback
    def transfer(self):
        def send_transaction(target_user):
            tx_creation_time = int(round(time.time() * 1000))
            response = self.wallet_rpc.transfer(self.username, target_user, 1, "BTS", "transferral", True)
            self.tx_info.append((tx_creation_time, response["signatures"][0]))

        t = Thread(target=send_transaction, args=("user%d" % (self.my_id + 1), ))
        t.daemon = True
        try:
            t.start()
        except RuntimeError:
            self._logger.warning("Unable to submit transaction - cannot start new thread!")

    @experiment_callback
    def dump_blockchain(self):
        """
        Dump the blockchain up to the latest block we have written
        """
        dynamic_settings = self.wallet_rpc.get_dynamic_global_properties()
        head_block_nr = dynamic_settings["head_block_number"]
        self._logger.info("Last block in blockchain: %d", head_block_nr)

        def write_blocks_async(last_block):
            with open("blockchain.txt", "a") as blockchain_file:
                for ind in range(self.last_block_written + 1, last_block + 1):
                    blockchain_file.write(json.dumps(self.wallet_rpc.get_block(ind)) + "\n")
                    self._logger.info("Written block %d...", ind)
                self.last_block_written = last_block

        t = Thread(target=write_blocks_async, args=(head_block_nr,))
        t.daemon = True
        t.start()

    @experiment_callback
    def write_stats(self):
        self._logger.info("Writing BitShares statistics...")

        if not self.is_client():
            # Write the disk usage of the data directory
            with open("disk_usage.txt", "w") as disk_out_file:
                dir_size = ExperimentModule.get_dir_size(self.data_dir)
                disk_out_file.write("%d" % dir_size)

        # Write a map with tx info
        with open("tx_submit_times.txt", "w") as created_tx_files:
            for order_tup in self.tx_info:
                created_tx_files.write("%d,%s\n" % (order_tup[0], order_tup[1]))

        if self.my_id == 1:
            with open("nathan_balance.txt", "w") as balances_file:
                balances_file.write(json.dumps(self.wallet_rpc.list_account_balances("nathan")))

        with open("balances.txt", "w") as balances_file:
            balances_file.write(json.dumps(self.wallet_rpc.list_account_balances(self.username)))
        with open("global_settings.txt", "w") as settings_file:
            settings_file.write(json.dumps(self.wallet_rpc.get_global_properties()))
        with open("dynamic_settings.txt", "w") as dynamic_settings_file:
            dynamic_settings_file.write(json.dumps(self.wallet_rpc.get_dynamic_global_properties()))
        with open("orderbook.txt", "w") as orderbook_file:
            orderbook_file.write(json.dumps(self.wallet_rpc.get_order_book("DUM1", "DUM2", 50)))
        # with open("orders.txt", "w") as orders_file:
        #    orders_file.write(json.dumps(self.wallet_rpc.get_limit_orders("DUM1", "DUM2", 10000)))
        with open("history.txt", "w") as history_file:
            history_file.write(json.dumps(self.wallet_rpc.get_account_history(self.username, 1000)))
        with open("witnesses.txt", "w") as witnesses_file:
            witnesses_file.write(json.dumps(self.wallet_rpc.list_witnesses("", 1000)))

        # Write a map of the order info
        with open("created_orders.txt", "w") as created_orders_file:
            for order_tup in self.orders_info:
                created_orders_file.write("%d,%s\n" % (order_tup[0], order_tup[1]))

        # Determine bandwidth usage
        total_up = 0
        total_down = 0
        connected_peers = self.wallet_rpc.network_get_connected_peers()
        for peer in connected_peers:
            total_up += peer["info"]["bytessent"]
            total_down += peer["info"]["bytesrecv"]

        with open("bandwidth.txt", "w") as bandwidth_file:
            bandwidth_file.write("%d,%d,%d" % (total_up, total_down, total_up + total_down))

    @experiment_callback
    def stop(self):
        print("Stopping BitShares...")
        if self.bs_process:
            self.bs_process.terminate()
        if self.wallet_process:
            self.wallet_process.terminate()

        if self.dump_blockchain_lc:
            self.dump_blockchain_lc.cancel()

        loop = get_event_loop()
        loop.stop()
