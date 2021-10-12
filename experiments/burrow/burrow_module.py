import json
import os
import random
import shutil
import signal
import string
import subprocess
import time
from asyncio import get_event_loop
from binascii import hexlify, unhexlify
from threading import Thread

import toml

from solcx import compile_files, set_solc_version

from web3 import Web3
from web3.exceptions import TimeExhausted

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule


class BurrowModule(BlockchainModule):

    def __init__(self, experiment):
        super().__init__(experiment)
        self.burrow_process = None
        self.validator_address = None
        self.deployed_contract_address = None
        self.deployed_contract_abi = None
        self.deployed_contract = None
        self.validator_addresses = {}
        self.experiment.message_callback = self

        self.submitted_transactions = {}
        self.confirmed_transactions = {}

    def on_all_vars_received(self):
        super().on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    @experiment_callback
    def transfer(self):
        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        def create_and_submit_tx():
            url = 'http://%s:%d' % (host, 12000 + validator_peer_id)
            w3 = Web3(Web3.HTTPProvider(url))
            random_id = ''.join(random.choice(string.ascii_uppercase) for _ in range(5))
            submit_time = int(round(time.time() * 1000))
            self.submitted_transactions[random_id] = submit_time

            tx_hash = self.deployed_contract.functions.transfer(
                w3.toChecksumAddress("EB77C5D07D50D9853EF90CB6B32E38755A9BDF2F"), 1, random_id).transact(
                {"from": w3.toChecksumAddress(self.validator_addresses[validator_peer_id])})
            try:
                _ = w3.eth.waitForTransactionReceipt(tx_hash)
                confirm_time = int(round(time.time() * 1000))
                self.confirmed_transactions[random_id] = confirm_time
            except TimeExhausted:
                print("Time exhausted for tx with hash: %d" % tx_hash)

        t = Thread(target=create_and_submit_tx)
        t.daemon = True
        t.start()

    def on_message(self, from_id, msg_type, msg):
        self._logger.info("Received message with type %s from peer %d", msg_type, from_id)
        if msg_type == b"validator_address":
            validator_address = msg.decode()
            self.validator_addresses[from_id] = validator_address
        elif msg_type == b"contract_address":
            self.deployed_contract_address = msg.decode()
        elif msg_type == b"contract_abi":
            self.deployed_contract_abi = json.loads(unhexlify(msg).decode())

        if self.deployed_contract_address and self.deployed_contract_abi:
            validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
            host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)
            url = 'http://%s:%d' % (host, 12000 + validator_peer_id)
            w3 = Web3(Web3.HTTPProvider(url))
            self.deployed_contract = w3.eth.contract(address=self.deployed_contract_address,
                                                     abi=self.deployed_contract_abi)

    @experiment_callback
    def generate_config(self):
        """
        Generate the initial configuration files.
        """
        self._logger.info("Generating Burrow config...")

        # Remove old config directory
        shutil.rmtree("/home/martijn/burrow_data", ignore_errors=True)

        os.mkdir("/home/martijn/burrow_data")

        cmd = "/home/martijn/burrow/burrow spec --validator-accounts=%d --full-accounts=1 > genesis-spec.json" % \
              (self.num_validators - 1)
        process = subprocess.Popen([cmd], shell=True, cwd='/home/martijn/burrow_data')
        process.wait()

        cmd = "/home/martijn/burrow/burrow configure --genesis-spec=genesis-spec.json --pool"
        process = subprocess.Popen([cmd], shell=True, cwd='/home/martijn/burrow_data')
        process.wait()

        # RSync the configuration with other nodes
        my_host, _ = self.experiment.get_peer_ip_port_by_id(self.experiment.my_id)
        other_hosts = set()
        for peer_id in self.experiment.all_vars.keys():
            host = self.experiment.all_vars[peer_id]['host']
            if host not in other_hosts and host != my_host:
                other_hosts.add(host)
                self._logger.info("Syncing config with host %s", host)
                os.system("rsync -r --delete /home/martijn/burrow_data martijn@%s:/home/martijn/" % host)

    @experiment_callback
    def start_burrow(self):
        """
        Start Hyperledger Burrow.
        """
        if self.is_client():
            return

        config_path = os.path.join(os.getcwd(), "burrow_data")
        shutil.copytree("/home/martijn/burrow_data", config_path)

        burrow_config_file_name = "burrow00%d.toml" % (self.experiment.my_id - 1)
        burrow_config_file_path = os.path.join(config_path, burrow_config_file_name)

        with open(os.path.join(config_path, burrow_config_file_path), "r") as burrow_config_file:
            content = burrow_config_file.read()
            node_config = toml.loads(content)
            node_config["Tendermint"]["ListenPort"] = "%d" % (10000 + self.experiment.my_id)
            node_config["Tendermint"]["ListenHost"] = "0.0.0.0"
            node_config["RPC"]["Web3"]["ListenPort"] = "%d" % (12000 + self.experiment.my_id)
            node_config["RPC"]["Web3"]["ListenHost"] = "0.0.0.0"
            node_config["RPC"]["Info"]["ListenPort"] = "%d" % (14000 + self.experiment.my_id)
            node_config["RPC"]["GRPC"]["ListenPort"] = "%d" % (16000 + self.experiment.my_id)

            self.validator_address = node_config["ValidatorAddress"]
            self.validator_addresses[self.my_id] = self.validator_address
            self._logger.info("Acting with validator address %s", self.validator_address)

            # Send the validator address to node 1 and all clients
            if self.my_id != 1:
                self.experiment.send_message(1, b"validator_address", self.validator_address.encode())
            for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
                self.experiment.send_message(client_index, b"validator_address", self.validator_address.encode())

            # Fix the persistent peers
            persistent_peers = node_config["Tendermint"]["PersistentPeers"].split(",")
            for peer_ind, persistent_peer in enumerate(persistent_peers):
                persistent_peer = persistent_peers[peer_ind]
                parts = persistent_peer.split(":")
                parts[-1] = "%d" % (10000 + peer_ind + 1)
                persistent_peer = ':'.join(parts)

                # Replace localhost IP
                host, _ = self.experiment.get_peer_ip_port_by_id(peer_ind + 1)
                persistent_peer = persistent_peer.replace("127.0.0.1", host)
                persistent_peers[peer_ind] = persistent_peer

            persistent_peers = ','.join(persistent_peers)
            node_config["Tendermint"]["PersistentPeers"] = persistent_peers

        with open(os.path.join(config_path, burrow_config_file_path), "w") as burrow_config_file:
            burrow_config_file.write(toml.dumps(node_config))

        cmd = "/home/martijn/burrow/burrow start --index %d --config %s > output.log 2>&1" % \
              (self.experiment.my_id - 1, burrow_config_file_name)
        self.burrow_process = subprocess.Popen([cmd], shell=True,  # pylint: disable=W1509
                                               cwd=config_path, preexec_fn=os.setsid)

        self._logger.info("Burrow started...")

    @experiment_callback
    def deploy_contract(self, contract_path, main_class_name):
        self._logger.info("Deploying contract...")

        set_solc_version('v0.6.2')

        url = 'http://localhost:%d' % (12000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))

        def deploy_contract_with_w3(w3, contract_interface):
            contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
            tx_hash = contract.constructor(100000000000).transact(
                {"from": w3.toChecksumAddress(self.validator_address)})
            address = w3.eth.waitForTransactionReceipt(tx_hash)['contractAddress']
            return address

        burrow_dir = os.path.dirname(os.path.realpath(__file__))
        full_contract_path = os.path.join(burrow_dir, "..", "ethereum", contract_path)
        if not os.path.exists(full_contract_path):
            self._logger.warning("Contract in path %s does not exist!", full_contract_path)
            return

        contract_dir = os.path.dirname(full_contract_path)

        cur_dir = os.getcwd()
        os.chdir(contract_dir)
        contract_name = os.path.basename(full_contract_path)
        self._logger.info("Compiling contract %s", contract_name)
        compiled_sol = compile_files([os.path.basename(full_contract_path)], optimize=True)
        os.chdir(cur_dir)

        contract_interface = compiled_sol["%s:%s" % (contract_name, main_class_name)]
        self._logger.info("Contract ABI: %s", contract_interface['abi'])
        address = deploy_contract_with_w3(w3, contract_interface)
        self._logger.info("Deployed contract to: %s", address)

        self.deployed_contract_address = address
        self.deployed_contract_abi = contract_interface['abi']

        for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
            # Send the necessary info to all clients
            self.experiment.send_message(client_index, b"contract_address", str(address).encode())
            self.experiment.send_message(client_index, b"contract_abi",
                                         hexlify(json.dumps(contract_interface['abi']).encode()))

        self.deployed_contract = w3.eth.contract(address=address, abi=contract_interface['abi'])

        # Transfer funds to other validator addresses
        for validator_id in range(2, self.num_validators + 1):
            tx_hash = self.deployed_contract.functions.transfer(
                w3.toChecksumAddress(self.validator_addresses[validator_id]), 100000, "AAAAA").transact(
                {"from": w3.toChecksumAddress(self.validator_address)})
            _ = w3.eth.waitForTransactionReceipt(tx_hash)

        # event_filter = self.deployed_contract.events.Transfer.createFilter(fromBlock='latest')
        #
        # # Listen for transfer events
        # async def log_loop():
        #     while True:
        #         for event in event_filter.get_new_entries():
        #             print("EVENT: %s" % event)
        #             complete_time = int(round(time.time() * 1000))
        #             tx_id = event["args"]["identifier"]
        #             self.confirmed_transactions[tx_id] = complete_time
        #         await sleep(0.5)
        #
        # ensure_future(log_loop())

    @experiment_callback
    def write_stats(self):
        """
        Write away statistics.
        """
        if self.is_client():
            # Write submitted transactions
            with open("submit_times.txt", "w") as tx_file:
                for tx_id, submit_time in self.submitted_transactions.items():
                    tx_file.write("%s,%d\n" % (tx_id, submit_time))

            # Write confirmed transactions
            with open("confirmed_txs.txt", "w") as tx_file:
                for tx_id, confirm_time in self.confirmed_transactions.items():
                    tx_file.write("%s,%d\n" % (tx_id, confirm_time))

        if self.is_client():
            return

        url = 'http://localhost:%d' % (12000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))

        # Dump blockchain
        latest_block = w3.eth.getBlock('latest')
        with open("blockchain.txt", "w") as out_file:
            for block_nr in range(1, latest_block.number + 1):
                block = w3.eth.getBlock(block_nr)
                out_file.write(w3.toJSON(block) + "\n")

    @experiment_callback
    def stop_burrow(self):
        print("Stopping Burrow...")

        if self.burrow_process:
            os.killpg(os.getpgid(self.burrow_process.pid), signal.SIGTERM)

        loop = get_event_loop()
        loop.stop()
