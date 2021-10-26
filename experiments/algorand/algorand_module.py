import hashlib
import json
import os
import shutil
import subprocess
import time
from binascii import hexlify
from random import sample
from threading import Thread

from algosdk import transaction
from algosdk.algod import AlgodClient
from algosdk.error import AlgodHTTPError, KMDHTTPError
from algosdk.kmd import KMDClient
from algosdk.wallet import Wallet

import requests

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import ExperimentModule


class AlgorandModule(BlockchainModule):

    def __init__(self, experiment):
        super(AlgorandModule, self).__init__(experiment)
        self.node_process = None
        self.kmd_process = None
        self.algod_client = None
        self.kmd_client = None
        self.algod_token = None
        self.kmd_token = None

        self.transactions = {}
        self.suggested_parameters = None
        self.wallet = None
        self.sender_key = None
        self.receiver_key = None
        self.tx_counter = 0

    def on_all_vars_received(self):
        super(AlgorandModule, self).on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    def get_data_dir(self, peer_id):
        return os.path.join("/tmp/algo_data_%d" % self.num_validators, "Node%d" % peer_id)

    def get_rest_token(self, peer_id):
        """
        Return the algod/kmd REST token for a specific peer.
        """
        hasher = hashlib.sha256()
        hasher.update(b"%d" % peer_id)
        return hexlify(hasher.digest()).decode()

    @experiment_callback
    def init_config(self):
        """
        Initialize the configuration of each node.
        """
        if self.is_client():
            return

        # Copy over the configuration to the local file system
        config_dir = "/tmp/algo_data_%d" % self.num_validators
        shutil.copytree(os.path.join(config_dir, "Node%d" % self.my_id), "Node%d" % self.my_id)

        self._logger.info("Initializing configuration...")
        data_dir = self.get_data_dir(self.my_id)

        with open(os.path.join(data_dir, "config.json"), "r") as config_file:
            content = config_file.read()
            json_content = json.loads(content)

        host, _ = self.experiment.get_peer_ip_port_by_id(self.my_id)
        json_content["EndpointAddress"] = "%s:%d" % (host, 18500 + self.my_id)
        json_content["NetAddress"] = "0.0.0.0:%d" % (13000 + self.my_id)

        with open(os.path.join(data_dir, "config.json"), "w") as config_file:
            config_file.write(json.dumps(json_content))

        # Change the KMD listen port
        with open(os.path.join(data_dir, "kmd-v0.5", "kmd_config.json.example"), "r") as kmd_config_file:
            content = kmd_config_file.read()
            json_content = json.loads(content)

        json_content["address"] = "%s:%d" % (host, 21000 + self.my_id)

        with open(os.path.join(data_dir, "kmd-v0.5", "kmd_config.json"), "w") as config_file:
            config_file.write(json.dumps(json_content))

        # Generate and persist the algod/kmd REST tokens
        rest_token = self.get_rest_token(self.my_id)
        self.algod_token = rest_token

        with open(os.path.join(data_dir, "algod.token"), "w") as algod_token_file:
            algod_token_file.write(rest_token)

        with open(os.path.join(data_dir, "kmd-v0.5", "kmd.token"), "w") as kmd_token_file:
            kmd_token_file.write(rest_token)

    @experiment_callback
    async def start_algorand_node(self):
        """
        Start an algorand node.
        """
        if self.is_client():
            return

        # Select 10 random peers to bootstrap with
        peers = list(range(1, self.num_validators + 1))
        peers.remove(self.my_id)
        random_peers = sample(peers, min(len(peers), 10))
        addresses = []
        for peer_id in random_peers:
            ip, _ = self.experiment.get_peer_ip_port_by_id(peer_id)
            addresses.append("%s:%d" % (ip, 13000 + peer_id))

        cmd = "goal node start -d %s -p %s" % (self.get_data_dir(self.my_id), ";".join(addresses))

        self._logger.info("Starting Algorand node with command: %s", cmd)
        self.node_process = subprocess.Popen(cmd.split(" "))

        kmd_cmd = "goal kmd start -d %s" % self.get_data_dir(self.my_id)
        self.kmd_process = subprocess.Popen(kmd_cmd.split(" "))

    @experiment_callback
    def start_client(self):
        # Find out to which validator we should connect
        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1

        self._logger.info("Starting Algorand client...")

        rest_token = self.get_rest_token(validator_peer_id)
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        # Start the algod client
        self.algod_client = AlgodClient(rest_token, "http://%s:%d" % (host, 18500 + validator_peer_id))

        # Start the kmd client
        self.kmd_client = KMDClient(rest_token, "http://%s:%d" % (host, 21000 + validator_peer_id))

    @experiment_callback
    def prepare_client(self):
        if not self.is_client():
            return

        self._logger.info("Fetching initial suggested parameters...")
        self.suggested_parameters = self.algod_client.suggested_params()
        self._logger.info("Received suggested parameters")
        self.suggested_parameters["fee"] = 1000  # start with 1000 fee

        self._logger.info("Fetching wallet info...")
        self.wallet = Wallet('unencrypted-default-wallet', '', self.kmd_client)
        wallet_keys = self.wallet.list_keys()
        self._logger.info("Wallet keys returned: %s", wallet_keys)

        # Determine the 'master' wallet with coins
        for wallet_key in wallet_keys:
            balance = self.algod_client.account_info(wallet_key)["amount"]
            if balance > 0:
                self._logger.info("Found account %s with balance %d", wallet_key, balance)
                self.sender_key = wallet_key
                break

        try:
            self.receiver_key = self.wallet.generate_key()
        except KMDHTTPError:
            self._logger.warning("Failed to generate receiver key!")

        self._logger.info("Sender key: %s", self.sender_key)
        self._logger.info("Receiver key: %s", self.receiver_key)

    @experiment_callback
    def transfer(self):
        if not self.is_client():
            return

        gen = self.suggested_parameters["genesisID"]
        gh = self.suggested_parameters["genesishashb64"]
        last_round = self.suggested_parameters["lastRound"]
        fee = self.suggested_parameters["fee"]

        def create_and_submit_tx():
            txn = transaction.PaymentTxn(self.sender_key, fee, last_round, last_round + 300, gh,
                                         self.receiver_key, 100000 + self.tx_counter, gen=gen, flat_fee=True)
            signed = self.wallet.sign_transaction(txn)
            submit_time = int(round(time.time() * 1000))
            try:
                self.tx_counter += 1
                self._logger.info("About to submit a transaction (fee: %d)", fee)
                tx_id = self.algod_client.send_transaction(signed)
                self.transactions[tx_id] = (submit_time, -1)
                self._logger.info("Submitted transaction with ID %s (fee: %d)", tx_id, fee)
            except AlgodHTTPError as e:
                msg = str(e)
                self._logger.error("Failed to submit transaction! %s", msg)

                if "below threshold" in msg:
                    parts = msg.split(" ")
                    new_fee = int(int(parts[-7]) * 1.2)
                    if new_fee <= 100000000:  # Surge pricing check
                        self.suggested_parameters["fee"] = new_fee
                        self._logger.info("Fixing fee to %d", self.suggested_parameters["fee"])

        t = Thread(target=create_and_submit_tx)
        t.daemon = True
        t.start()

    @experiment_callback
    def print_status(self):
        self._logger.info("Getting Algorand status...")

        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1

        rest_token = self.get_rest_token(validator_peer_id)
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)
        response = requests.get("http://%s:%d/metrics" % (host, 18500 + validator_peer_id),
                                headers={"X-Algo-API-Token": rest_token})
        print(response.text)

        response = requests.get("http://%s:%d/v2/status" % (host, 18500 + validator_peer_id),
                                headers={"X-Algo-API-Token": rest_token})
        print(response.text)

    @experiment_callback
    def write_info(self):
        if not self.is_client():
            self._logger.info("Writing disk usage...")
            # Write the disk usage of the data directory
            with open("disk_usage.txt", "w") as disk_out_file:
                dir_size = ExperimentModule.get_dir_size(self.get_data_dir(self.my_id))
                disk_out_file.write("%d" % dir_size)

            return

        # Get the confirmation times of all transactions and write them away
        last_round = self.algod_client.suggested_params()["lastRound"]
        self._logger.info("Last round: %d", last_round)
        for round_nr in range(1, last_round + 1):
            self._logger.info("Fetching block %d...", round_nr)
            block_info = self.algod_client.block_info(round_nr)
            timestamp = (block_info["timestamp"] + 1) * 1000  # +1 since this timestamp is rounded down
            if 'txns' in block_info:
                if 'transactions' in block_info['txns']:
                    self._logger.info("Transactions in round %d: %d", round_nr, len(block_info['txns']['transactions']))
                    for tx in block_info['txns']['transactions']:
                        tx_id = tx["tx"]
                        if tx_id in self.transactions:
                            self.transactions[tx_id] = (self.transactions[tx_id][0], timestamp)

        # Write transactions
        with open("transactions.txt", "w") as tx_file:
            for tx_id, tx_info in self.transactions.items():
                tx_file.write("%s,%d,%d\n" % (tx_id, tx_info[0], tx_info[1]))

    @experiment_callback
    def stop_algorand(self):
        if self.is_client():
            return

        os.system("pkill -f algod")
        os.system("pkill -f kmd")
