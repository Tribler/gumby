import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import time
from asyncio import get_event_loop, sleep
from binascii import hexlify
from threading import Thread

import requests

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import ExperimentModule


class AvalancheModule(BlockchainModule):

    def __init__(self, experiment):
        super().__init__(experiment)
        self.avalanche_process = None
        self.avax_address = None
        self.avax_addresses = {}
        self.node_ids = {}
        self.bootstrap_node_ids = {}
        self.transactions = {}
        self.experiment.message_callback = self
        self.data_dir = None

    def on_id_received(self):
        super().on_id_received()
        self.data_dir = os.path.join("/tmp", "avalanche_data_%d" % self.my_id)

    def on_all_vars_received(self):
        super().on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    def on_message(self, from_id, msg_type, msg):
        self._logger.info("Received message with type %s from peer %d", msg_type, from_id)
        if msg_type == b"avax_address":
            avax_address = msg.decode()
            self.avax_addresses[from_id] = avax_address
        elif msg_type == b"node_id":
            self.node_ids[from_id] = "NodeID-%s" % msg.decode()
        elif msg_type == b"bootstrap_node_id":
            self.bootstrap_node_ids[from_id] = "NodeID-%s" % msg.decode()

    @experiment_callback
    def sync_staking_keys(self):
        # More staking keys can be generated using the following command
        # (on surfnet1, in /home/martijn/avalanche/staking):
        # /home/martijn/go/bin/go run gen_staker_key.go <PEER_ID_HERE>
        my_host, _ = self.experiment.get_peer_ip_port_by_id(self.experiment.my_id)
        other_hosts = set()
        for peer_id in self.experiment.all_vars.keys():
            host = self.experiment.all_vars[peer_id]['host']
            if host not in other_hosts and host != my_host:
                other_hosts.add(host)
                self._logger.info("Syncing staking keys with host %s", host)
                os.system("rsync -r --delete /home/martijn/avalanche/staking martijn@%s:/home/martijn/avalanche" % host)

    @experiment_callback
    async def share_node_id(self):
        """
        Start avalanche for one second and get the node ID from the log. Then share it with other nodes.
        """
        if self.is_client():
            return

        http_port = 12000 + self.my_id
        staking_port = 14000 + self.my_id
        my_host, _ = self.experiment.get_peer_ip_port_by_id(self.my_id)

        snow_sample_size = min(20, self.num_validators / 2)
        snow_quorum_size = min(14, self.num_validators / 2)

        cmd = "/home/martijn/avalanche/avalanchego --public-ip=%s --snow-sample-size=%d --snow-quorum-size=%d " \
              "--http-host= --http-port=%s --staking-port=%s --db-dir=%s --staking-enabled=true " \
              "--network-id=local --bootstrap-ips= conn-meter-max-conns=0 --max-non-staker-pending-msgs=1000 " \
              "--staking-tls-cert-file=/home/martijn/avalanche/staking/local/staker%d.crt " \
              "--plugin-dir=/home/martijn/avalanche/plugins " \
              "--staking-tls-key-file=/home/martijn/avalanche/staking/local/staker%d.key > avalanche.out" % \
              (my_host, snow_sample_size, snow_quorum_size, http_port, staking_port,
               self.data_dir, self.my_id, self.my_id)

        avalanche_process = subprocess.Popen([cmd], shell=True, preexec_fn=os.setsid)  # pylint: disable=W1509
        await sleep(2)
        os.killpg(os.getpgid(avalanche_process.pid), signal.SIGKILL)

        # Reset the database
        shutil.rmtree(self.data_dir)

        # Read the Avalanche log and extract the node ID
        node_id = None
        with open("avalanche.out") as ava_log_file:
            for line in ava_log_file.readlines():
                if "Set node's ID to" in line:
                    node_id = line.split(" ")[-1]

        # Select 10 random peers that bootstrap with this peer
        peers = list(range(1, self.num_validators + 1))
        peers.remove(self.my_id)
        random_peers = random.sample(peers, min(len(peers), 10))
        for peer_id in random_peers:
            self.experiment.send_message(peer_id, b"bootstrap_node_id", node_id.encode())

        if self.my_id > 5:
            # Also share the node ID with node 1
            self.experiment.send_message(1, b"node_id", node_id.encode())

    @experiment_callback
    async def start_avalanche(self):
        """
        Start an Avalanche node.
        """
        self._logger.info("This is node %d", self.my_id)

        if self.is_client():
            return

        http_port = 12000 + self.my_id
        staking_port = 14000 + self.my_id
        my_host, _ = self.experiment.get_peer_ip_port_by_id(self.my_id)

        # Construct the list with bootstrap IPs
        bootstrap_ips = []
        bootstrap_ids = []
        for bootstrap_peer_id, bootstrap_node_id in self.bootstrap_node_ids.items():
            host, _ = self.experiment.get_peer_ip_port_by_id(bootstrap_peer_id)
            bootstrap_ips.append("%s:%d" % (host, 14000 + bootstrap_peer_id))
            bootstrap_ids.append(bootstrap_node_id)

        snow_sample_size = min(20, self.num_validators / 2)
        snow_quorum_size = min(14, self.num_validators / 2)

        cmd = "/home/martijn/avalanche/avalanchego --public-ip=%s --snow-sample-size=%d --snow-quorum-size=%d " \
              "--http-host= --http-port=%s --staking-port=%s --db-dir=%s --staking-enabled=true " \
              "--network-id=local --bootstrap-ips=%s --bootstrap-ids=%s conn-meter-max-conns=0 " \
              "--max-non-staker-pending-msgs=1000 " \
              "--staking-tls-cert-file=/home/martijn/avalanche/staking/local/staker%d.crt " \
              "--plugin-dir=/home/martijn/avalanche/plugins " \
              "--staking-tls-key-file=/home/martijn/avalanche/staking/local/staker%d.key" % \
              (my_host, snow_sample_size, snow_quorum_size, http_port, staking_port,
               self.data_dir, ",".join(bootstrap_ips), ",".join(bootstrap_ids), self.my_id, self.my_id)
        self._logger.info("Starting Avalanche with command: %s...", cmd)

        file_out = open("avalanche.out", "w")
        self.avalanche_process = subprocess.Popen(cmd.split(" "), stdout=file_out)

    @experiment_callback
    def create_keystore_user(self):
        if self.is_client():
            return

        self._logger.info("Creating keystore user...")

        payload = {
            "method": "keystore.createUser",
            "params": [{
                "username": "peer%d" % self.my_id,
                "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode()
            }],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post("http://localhost:%d/ext/keystore" % (12000 + self.my_id), json=payload).json()
        self._logger.info("Create keystore response: %s", response)

    @experiment_callback
    def import_funds(self):
        if self.is_client():
            return

        self._logger.info("Importing initial funds...")

        payload = {
            "method": "avm.importKey",
            "params": [{
                "username": "peer%d" % self.my_id,
                "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
                "privateKey": "PrivateKey-ewoqjP7PxY4yr3iLTpLisriqt94hdyDFNgchSxGGztUrTXtNN"
            }],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post("http://localhost:%d/ext/bc/X" % (12000 + self.my_id), json=payload).json()
        self._logger.info("Import funds response: %s", response)
        self.avax_address = response["result"]["address"]

        for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
            self.experiment.send_message(client_index, b"avax_address", self.avax_address.encode())

    @experiment_callback
    def create_address(self):
        if self.is_client() or self.my_id == 1:  # The first node uses the initial address
            return

        self._logger.info("Creating address...")

        payload = {
            "method": "avm.createAddress",
            "params": [{
                "username": "peer%d" % self.my_id,
                "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
            }],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post("http://localhost:%d/ext/bc/X" % (12000 + self.my_id), json=payload).json()
        self._logger.info("Create address response: %s", response)
        self.avax_address = response["result"]["address"]

        # Send the address to the first node
        self.experiment.send_message(1, b"avax_address", self.avax_address.encode())

        # Send the address to the clients
        for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
            self.experiment.send_message(client_index, b"avax_address", self.avax_address.encode())

    @experiment_callback
    async def transfer_funds_to_others(self):
        if self.is_client():
            return

        self._logger.info("Transferring funds to others...")

        for avax_address in self.avax_addresses.values():
            self._logger.info("Transferring initial funds to address %s", avax_address)
            payload = {
                "method": "wallet.send",
                "params": [{
                    "assetID": "AVAX",
                    "amount": 100000000000,
                    "to": avax_address,
                    "username": "peer%d" % self.my_id,
                    "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
                }],
                "jsonrpc": "2.0",
                "id": 0,
            }

            response = requests.post("http://localhost:%d/ext/bc/X/wallet" % (12000 + self.my_id), json=payload).json()
            self._logger.info("Transfer funds response: %s", response)

    @experiment_callback
    async def register_validators(self):
        if self.is_client():
            return

        self._logger.info("Registering validators...")

        # Import the bootstrap address in the P chain
        payload = {
            "method": "platform.importKey",
            "params": [{
                "username": "peer%d" % self.my_id,
                "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
                "privateKey": "PrivateKey-ewoqjP7PxY4yr3iLTpLisriqt94hdyDFNgchSxGGztUrTXtNN"
            }],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post("http://localhost:%d/ext/P" % (12000 + self.my_id), json=payload).json()
        self._logger.info("Import funds response: %s", response)
        staking_address = response["result"]["address"]

        for validator_id, node_id in self.node_ids.items():
            # Create a reward address
            payload = {
                "method": "platform.createAddress",
                "params": [{
                    "username": "peer%d" % self.my_id,
                    "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
                }],
                "jsonrpc": "2.0",
                "id": 0,
            }

            response = requests.post("http://localhost:%d/ext/bc/P" % (12000 + self.my_id), json=payload).json()
            self._logger.info("Create address response: %s", response)
            reward_address = response["result"]["address"]

            # Register as validator
            payload = {
                "method": "platform.addValidator",
                "params": [{
                    "nodeID": node_id,
                    "from": [staking_address],
                    "startTime": '%d' % (int(time.time()) + 15),
                    "endTime": '%d' % (int(time.time()) + 30 * 24 * 3600),
                    "stakeAmount": 2000000000000,
                    "rewardAddress": reward_address,
                    "delegationFeeRate": 10,
                    "username": "peer%d" % self.my_id,
                    "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
                }],
                "jsonrpc": "2.0",
                "id": 0,
            }

            response = requests.post("http://localhost:%d/ext/P" % (12000 + self.my_id), json=payload).json()
            self._logger.info("Add validator response: %s", response)
            tx_id = response["result"]["txID"]

            while True:
                self._logger.info("Getting status of validator tx (%d)", validator_id)
                payload = {
                    "method": "platform.getTxStatus",
                    "params": [{
                        "txID": tx_id,
                        "includeReason": True,
                    }],
                    "jsonrpc": "2.0",
                    "id": 0,
                }

                response = requests.post("http://localhost:%d/ext/P" % (12000 + self.my_id), json=payload).json()
                self._logger.info("Validator tx status: %s", response)
                if response["result"]["status"] == "Committed":
                    break
                await sleep(0.1)

    @experiment_callback
    def transfer(self):
        if not self.is_client():
            return

        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
        validator_host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        def create_and_submit_tx():
            self._logger.info("Creating transaction")
            submit_time = int(round(time.time() * 1000))

            payload = {
                "method": "wallet.send",
                "params": [{
                    "assetID": "AVAX",
                    "amount": 100,
                    "to": self.avax_addresses[validator_peer_id],
                    "username": "peer%d" % validator_peer_id,
                    "password": hexlify(hashlib.md5(b'peer%d' % validator_peer_id).digest()).decode(),
                }],
                "jsonrpc": "2.0",
                "id": 0,
            }

            response = requests.post("http://%s:%d/ext/bc/X/wallet" %
                                     (validator_host, 12000 + validator_peer_id), json=payload).json()
            self._logger.info("Transfer funds response: %s", response)
            tx_id = response["result"]["txID"]
            self.transactions[tx_id] = (submit_time, -1)

            # Poll the status of this transaction
            for _ in range(20):
                payload = {
                    "method": "avm.getTxStatus",
                    "params": [{
                        "txID": tx_id,
                    }],
                    "jsonrpc": "2.0",
                    "id": 0,
                }

                response = requests.post("http://%s:%d/ext/bc/X" %
                                         (validator_host, 12000 + validator_peer_id), json=payload).json()
                self._logger.info("Poll response for tx %s: %s", tx_id, response)
                if response["result"]["status"] == "Accepted":
                    confirm_time = int(round(time.time() * 1000))
                    self.transactions[tx_id] = (self.transactions[tx_id][0], confirm_time)
                    break
                elif response["result"]["status"] == "Dropped":
                    self._logger.info("Transaction %s dropped! Response: %s", tx_id, response["result"])
                    break
                elif response["result"]["status"] == "Rejected":
                    self._logger.info("Transaction %s rejected! Response: %s", tx_id, response["result"])
                    break

                time.sleep(0.5)

        t = Thread(target=create_and_submit_tx)
        t.daemon = True
        t.start()

    @experiment_callback
    def write_stats(self):
        if self.is_client():
            # Write transactions
            with open("transactions.txt", "w") as tx_file:
                for tx_id, tx_info in self.transactions.items():
                    tx_file.write("%s,%d,%d\n" % (tx_id, tx_info[0], tx_info[1]))

            return

        # Write the disk usage of the data directory
        with open("disk_usage.txt", "w") as disk_out_file:
            dir_size = ExperimentModule.get_dir_size(self.data_dir)
            disk_out_file.write("%d" % dir_size)

        # Write the addresses managed by this user
        payload = {
            "method": "platform.listAddresses",
            "params": [{
                "username": "peer%d" % self.my_id,
                "password": hexlify(hashlib.md5(b'peer%d' % self.my_id).digest()).decode(),
            }],
            "jsonrpc": "2.0",
            "id": 0,
        }

        response = requests.post("http://localhost:%d/ext/bc/P" % (12000 + self.my_id), json=payload).json()
        with open("addresses.txt", "w") as addresses_file:
            addresses_file.write(json.dumps(response["result"]["addresses"]))

        # Write the balance
        # payload = {
        #     "method": "avm.getBalance",
        #     "params": [{
        #         "address": self.avax_address,
        #         "assetID": "AVAX"
        #     }],
        #     "jsonrpc": "2.0",
        #     "id": 0,
        # }
        #
        # self._logger.info("Requesting balances...")
        # response = requests.post("http://localhost:%d/ext/bc/X" % (12000 + self.my_id), json=payload).json()
        # self._logger.info("Request balance response: %s" % response)
        # with open("balance.txt", "w") as balance_file:
        #     balance_file.write(response["result"]["balance"])

        # Write the current validators
        payload = {
            "method": "platform.getCurrentValidators",
            "params": [{}],
            "jsonrpc": "2.0",
            "id": 0,
        }

        self._logger.info("Requesting validators...")
        response = requests.post("http://localhost:%d/ext/P" % (12000 + self.my_id), json=payload).json()
        with open("validators.txt", "w") as validators_file:
            validators_file.write(json.dumps(response["result"]))

    @experiment_callback
    def stop(self):
        if self.avalanche_process:
            os.system("pkill -f avalanchego")
            os.system("pkill -f evm")

        loop = get_event_loop()
        loop.stop()
