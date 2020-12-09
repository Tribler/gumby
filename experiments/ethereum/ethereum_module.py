import json
import os
import random
import subprocess
import time
from asyncio import get_event_loop, sleep, ensure_future
from binascii import hexlify, unhexlify

from shutil import copyfile

import requests

from solcx import compile_files, set_solc_version

from web3 import Web3

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import static_module
from gumby.util import run_task


@static_module
class EthereumModule(BlockchainModule):

    def __init__(self, experiment):
        super(EthereumModule, self).__init__(experiment)
        self.ethereum_process = None
        self.public_key = None
        self.deployed_contract_address = None
        self.deployed_contract_abi = None
        self.experiment.message_callback = self
        self.others_public_keys = {}
        self.network_id = 3248394248
        self.tx_pool_polls = []
        self.poll_start_time = None
        self.tx_pool_lc = None
        self.submitted_transactions = {}
        self.confirmed_transactions = {}

    def on_message(self, from_id, msg_type, msg):
        self._logger.info("Received message with type %s from peer %d", msg_type, from_id)
        if msg_type == b"contract_address":
            self.deployed_contract_address = msg.decode()
        elif msg_type == b"contract_abi":
            self.deployed_contract_abi = json.loads(unhexlify(msg).decode())
        elif msg_type == b"public_key":
            self.others_public_keys[from_id] = msg.decode()

    @experiment_callback
    def generate_keypair(self):
        """
        Generate a keypair with the command: geth account new --datadir data --password password.txt
        """
        if self.is_client():
            return

        with open("password.txt", "w") as password_file:
            password_file.write("password")

        cmd = "geth account new --datadir data --password password.txt"
        process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()

        pub_key = None
        out, _ = process.communicate()
        for line in out.split(b"\n"):
            if b"Public address of the key" in line:
                pub_key = line.split(b" ")[-1][2:].lower()
                break

        if pub_key:
            self.public_key = pub_key.decode()
            self._logger.info("Public key: %s", pub_key.decode())

            if self.experiment.my_id == 1:
                self.others_public_keys[1] = self.public_key
            else:
                self.experiment.send_message(1, b"public_key", self.public_key.encode())

            for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
                self.experiment.send_message(client_index, b"public_key", self.public_key.encode())

    @experiment_callback
    def connect_to_nodes(self):
        self._logger.info("Connecting to bootstrap node...")

        all_peer_ids = list(self.all_vars.keys())
        peer_ids = random.sample(all_peer_ids, min(len(all_peer_ids), 50))

        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))

        for peer_id in peer_ids:
            self._logger.info("Connecting to peer %s", peer_id)
            with open("/home/pouwelse/ethash/ethereum_node_%s" % peer_id, "r") as bootstrap_node_file:
                bootstrap_enode = json.loads(bootstrap_node_file.read())["enode"]
                w3.geth.admin.add_peer(bootstrap_enode)

    @experiment_callback
    def generate_genesis(self):
        """
        Generate the initial genesis file.
        """
        self._logger.info("Generating Ethereum genesis file...")

        alloc_json = {}
        for public_key in self.others_public_keys.values():
            alloc_json[public_key] = {"balance": "1000000000000000000"}

        if "MINING_DIFFICULTY" in os.environ:
            difficulty = str(os.environ["MINING_DIFFICULTY"])
        else:
            # This number is based on the DAS5 CPUs, with an average block time of 13 seconds.
            difficulty = "%d" % (55000 * 13 * self.num_validators)

        if "GAS_LIMIT" in os.environ:
            gas_limit = str(os.environ["GAS_LIMIT"])
        else:
            gas_limit = "10000000"

        genesis_json = {
            "config": {
                "chainId": self.network_id,
                "homesteadBlock": 0,
                "eip150Block": 0,
                "eip155Block": 0,
                "eip158Block": 0,
                "byzantiumBlock": 0,
                "constantinopleBlock": 0,
                "petersburgBlock": 0,
                "ethash": {}
            },
            "nonce": "0x0000000000000000",
            "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "difficulty": difficulty,  # Base the difficulty on the number of total peers
            "gasLimit": gas_limit,
            "alloc": alloc_json
        }

        with open("/home/pouwelse/genesis.json", "w") as genesis_json_file:
            genesis_json_file.write(json.dumps(genesis_json))

    @experiment_callback
    def initialize_chain(self):
        """
        Initialize the blockchain data directory.
        """
        if self.is_client():
            return

        self._logger.info("Initializing blockchain data dir...")

        copyfile("/home/pouwelse/genesis.json", "genesis.json")

        cmd = "geth init --datadir data genesis.json"
        process = subprocess.Popen([cmd], shell=True)
        process.wait()

        self._logger.info("Blockchain data dir initialized.")

    @experiment_callback
    async def start_ethereum(self):
        """
        Start an Ethereum node.
        """
        if self.is_client():
            return

        port = 12000 + self.experiment.my_id
        rpc_port = 14000 + self.experiment.my_id
        pprof_port = 16000 + self.experiment.my_id

        host, _ = self.experiment.get_peer_ip_port_by_id(str(self.experiment.my_id))
        if self.experiment.my_id == 1:
            cmd = "geth --datadir data --allow-insecure-unlock --metrics --pprof --pprofport %d --rpc --rpcport %d " \
                  "--rpcaddr 0.0.0.0 " \
                  "--rpcapi=\"eth,net,web3,personal,admin,debug,txpool\" --ethash.dagdir /home/pouwelse/ethash " \
                  "--port %d --networkid %d --nat extip:%s --mine --miner.threads=1 --maxpeers 500 " \
                  "--netrestrict 10.141.0.0/24 --txpool.globalslots=20000 " \
                  "--txpool.globalqueue=20000 > ethereum.out 2>&1" % (pprof_port, rpc_port, port, self.network_id, host)
        else:
            start_delay = random.random() * 10
            await sleep(start_delay)

            with open("/home/pouwelse/ethash/ethereum_node_1", "r") as bootstrap_node_file:
                bootstrap_enode = json.loads(bootstrap_node_file.read())["enode"]
            cmd = "geth --datadir data --allow-insecure-unlock --metrics --pprof --pprofport %d --rpc --rpcport %d " \
                  "--rpcaddr 0.0.0.0 " \
                  "--rpcapi=\"eth,net,web3,personal,admin,debug,txpool\" --ethash.dagdir /home/pouwelse/ethash " \
                  "--port %d --networkid %d --nat extip:%s --mine --miner.threads=1 --maxpeers 500 " \
                  "--netrestrict 10.141.0.0/24 --txpool.globalslots=20000 --txpool.globalqueue=20000 " \
                  "--bootnodes %s > ethereum.out 2>&1" \
                  % (pprof_port, rpc_port, port, self.network_id, host, bootstrap_enode)

        self._logger.info("Ethereum start command: %s", cmd)

        self.ethereum_process = subprocess.Popen([cmd], shell=True)
        self._logger.info("Ethereum started...")

    @experiment_callback
    def start_monitor_tx_pool(self):
        """
        Start monitoring the tx pool.
        """
        self._logger.info("Starting to monitor the tx pool")
        self.poll_start_time = int(round(time.time() * 1000))

        def monitor_tx_pool():
            url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
            w3 = Web3(Web3.HTTPProvider(url))
            tx_pool_status = json.loads(Web3.toJSON(w3.geth.txpool.status()))
            time_elapsed = int(round(time.time() * 1000)) - self.poll_start_time
            self.tx_pool_polls.append((time_elapsed, int(tx_pool_status["pending"], 16),
                                       int(tx_pool_status["queued"], 16)))

        self.tx_pool_lc = run_task(monitor_tx_pool, interval=1.0)

    @experiment_callback
    def stop_monitor_tx_pool(self):
        self._logger.info("Stopping monitor of the tx poll")
        self.tx_pool_lc.cancel()
        self.tx_pool_lc = None

    @experiment_callback
    def unlock_account(self):
        if self.is_client():
            return

        self._logger.info("Unlocking account...")
        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))
        w3.geth.personal.unlockAccount(w3.toChecksumAddress(self.public_key), "password", 0)
        self._logger.info("Account unlocked!")

    @experiment_callback
    def write_node_info(self):
        """
        Write node connection info.
        """
        self._logger.info("Writing node info...")
        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))
        node_info = w3.geth.admin.node_info()

        with open("/home/pouwelse/ethash/ethereum_node_%d" % self.experiment.my_id, "w") as out_file:
            out_file.write(w3.toJSON(node_info))

    @experiment_callback
    def print_connected_peers(self):
        """
        Print the connected peers.
        """
        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))
        peers = w3.geth.admin.peers()
        print("Network peers: %s" % peers)

    @experiment_callback
    def print_balance(self):
        """
        Print the Ethereum balance of this node.
        """
        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))
        print("Balance: %d" % w3.eth.getBalance(Web3.toChecksumAddress("0x" + self.public_key)))

    @experiment_callback
    def transfer(self):
        """
        Transfer some ether to another account.
        """
        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)

        payload = {
            "method": "personal_sendTransaction",
            "params": [{
                "from": "0x" + self.public_key,
                "to": "0xafa3f8684e54059998bc3a7b0d2b0da075154d66",  # TODO: we should make this dynamic
                "value": hex(100000)
            }, "password"],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post(url, json=payload).json()
        self._logger.info("Transfer response: %s", response)

    @experiment_callback
    def deploy_contract(self, contract_path, main_class_name):
        self._logger.info("Deploying contract...")

        set_solc_version('v0.6.2')

        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))

        def deploy_contract_with_w3(w3, contract_interface):
            contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
            tx_hash = contract.constructor(100000000000).transact({"from": w3.eth.accounts[0]})
            address = w3.eth.waitForTransactionReceipt(tx_hash)['contractAddress']
            return address

        ethereum_dir = os.path.dirname(os.path.realpath(__file__))
        full_contract_path = os.path.join(ethereum_dir, contract_path)
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

        for str_client_id in self.all_vars.keys():
            client_id = int(str_client_id)
            if client_id == self.experiment.my_id:
                continue

            self.experiment.send_message(client_id, b"contract_address", str(address).encode())
            self.experiment.send_message(client_id, b"contract_abi",
                                         hexlify(json.dumps(contract_interface['abi']).encode()))

        contract = w3.eth.contract(address=address, abi=contract_interface['abi'])
        event_filter = contract.events.Transfer.createFilter(fromBlock='latest')

        # Listen for transfer events
        async def log_loop():
            while True:
                for event in event_filter.get_new_entries():
                    print("EVENT: %s" % event)
                    complete_time = int(round(time.time() * 1000))
                    tx_id = event["args"]["identifier"]
                    self.confirmed_transactions[tx_id] = complete_time
                await sleep(0.5)

        ensure_future(log_loop())

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

            return

        # Write confirmed transactions
        with open("confirmed_txs.txt", "w") as tx_file:
            for tx_id, confirm_time in self.confirmed_transactions.items():
                tx_file.write("%s,%d\n" % (tx_id, confirm_time))

        url = 'http://localhost:%d/debug/metrics' % (16000 + self.experiment.my_id)
        response = requests.get(url).text
        with open("metrics.txt", "w") as metrics_file:
            metrics_file.write(response)

        # Get bandwidth statistics
        metrics_json = json.loads(response)
        total_up = metrics_json["p2p/egress.count"]
        total_down = metrics_json["p2p/ingress.count"]
        with open("bandwidth.txt", "w") as bandwidth_file:
            bandwidth_file.write("%d,%d,%d" % (total_up, total_down, total_up + total_down))

        url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
        w3 = Web3(Web3.HTTPProvider(url))

        # Dump tx pool status
        print("TX pool status: %s" % w3.geth.txpool.status())

        # Dump tx pool polls
        if self.tx_pool_polls:
            with open("tx_pool.txt", "w") as tx_pool_file:
                for poll_time, num_pending, num_queued in self.tx_pool_polls:
                    tx_pool_file.write("%f,%d,%d\n" % (poll_time, num_pending, num_queued))

        # Dump hash rate
        with open("hashrate.txt", "w") as hash_rate_file:
            hash_rate_file.write("%s" % w3.eth.hashrate)

        # Dump blockchain
        latest_block = w3.eth.getBlock('latest')
        with open("blockchain.txt", "w") as out_file:
            for block_nr in range(1, latest_block.number + 1):
                block = w3.eth.getBlock(block_nr)
                out_file.write(w3.toJSON(block) + "\n")

    @experiment_callback
    def stop_ethereum(self):
        self._logger.info("Stopping Ethereum...")

        if self.ethereum_process:
            self.ethereum_process.kill()

        loop = get_event_loop()
        loop.stop()
