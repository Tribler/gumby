import json
import os
import subprocess
import time
from asyncio import get_event_loop, sleep

import aiohttp

from diem import LocalAccount, chain_ids, diem_types, jsonrpc, stdlib, testnet, utils

from ruamel.yaml import YAML

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import ExperimentModule
from gumby.util import run_task


MAX_MINT = 10 ** 19  # 10 trillion libras


class LibraModule(BlockchainModule):

    def __init__(self, experiment):
        super(LibraModule, self).__init__(experiment)
        self.libra_validator_process = None
        self.diem_client = None
        self.faucet_client = None
        self.libra_path = "/home/martijn/diem"
        self.validator_config = None
        self.validator_id = None
        self.validator_ids = None
        self.peer_ids = {}
        self.validator_network_ids = {}
        self.sender_account = None
        self.receiver_account = None
        self.tx_info = {}
        self.last_tx_confirmed = -1

        self.monitor_lc = None
        self.current_seq_num = 0

    def on_all_vars_received(self):
        super(LibraModule, self).on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    @experiment_callback
    def init_config(self):
        """
        Initialize the configuration. In particular, make sure the addresses of the seed nodes are correctly set.
        """
        diem_config_root_dir = os.path.join("/tmp", "diem_data_%d" % self.num_validators)

        self.validator_id = self.my_id - 1
        if self.is_client():
            return

        self._logger.info("Extracting network identifiers...")

        for validator_id in range(0, self.num_validators):
            self._logger.info("Reading initial config of validator %d...", validator_id)

            yaml = YAML()
            with open(os.path.join(diem_config_root_dir, "%d" % validator_id, "node.yaml"), "r") as node_config_file:
                node_config = yaml.load(node_config_file)

            old_validator_network_listen_address = node_config["validator_network"]["listen_address"]
            old_validator_network_listen_port = int(old_validator_network_listen_address.split("/")[-1])

            log_path = os.path.join(diem_config_root_dir, "logs", "%d.log" % validator_id)
            with open(log_path, "r") as log_file:
                for line in log_file.readlines():
                    if "Start listening for incoming connections on" in line:
                        full_network_string = line.split(" ")[10]
                        port = int(full_network_string.split("/")[4])
                        if port == old_validator_network_listen_port:
                            self._logger.info("Network ID of validator %d: %s", validator_id, full_network_string)

                            # Get the peer ID
                            peer_id = json.loads(line.split(" ")[-1])["network_context"]["peer_id"]
                            self._logger.info("Peer ID of validator %d: %s", validator_id, peer_id)
                            self.peer_ids[validator_id] = peer_id

                            # Modify the network string to insert the right IP address
                            host, _ = self.experiment.get_peer_ip_port_by_id(validator_id + 1)
                            parts = full_network_string.split("/")
                            parts[2] = host
                            full_network_string = "/".join(parts)

                            self.validator_network_ids[validator_id] = full_network_string
                            break

        self._logger.info("Modifying configuration file...")

        # Write the new configuration file
        yaml = YAML()
        with open(os.path.join(diem_config_root_dir, "%d" % self.validator_id, "node.yaml"), "r") as node_config_file:
            node_config = yaml.load(node_config_file)

        node_config["mempool"]["capacity_per_user"] = 10000
        node_config["consensus"]["max_block_size"] = 10000
        node_config["execution"]["genesis_file_location"] = os.path.join("/tmp", "diem_data_%d" % self.num_validators,
                                                                         "%d" % self.validator_id, "genesis.blob")
        node_config["json_rpc"]["address"] = "0.0.0.0:%d" % (12000 + self.my_id)

        for validator_id, network_string in self.validator_network_ids.items():
            if validator_id == self.validator_id:
                continue
            node_config["validator_network"]["seed_addrs"][self.peer_ids[validator_id]] = [network_string]

        with open(os.path.join(os.getcwd(), "node.yaml"), "w") as crypto_config_file:
            yaml.dump(node_config, crypto_config_file)

    @experiment_callback
    def start_libra_validator(self):
        # Read the config
        if self.is_client():
            return

        self._logger.info("Starting libra validator with id %s...", self.validator_id)
        libra_exec_path = os.path.join(self.libra_path, "target", "release", "diem-node")
        config_path = os.path.join(os.getcwd(), "node.yaml")

        cmd = '%s -f %s' % (libra_exec_path, config_path)
        out_file = open("diem_output.log", "w")
        self.libra_validator_process = subprocess.Popen(cmd.split(" "), stdout=out_file, stderr=out_file)

    @experiment_callback
    async def start_libra_cli(self):
        # Get the faucet host
        faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)

        if self.my_id == 1:
            self._logger.info("Starting faucet!")
            # Start the minting service
            mint_key_path = os.path.join("/tmp", "diem_data_%d" % self.num_validators, "mint.key")
            out_file = open("faucet.out", "w")
            cmd = "%s/target/release/diem-faucet -m %s -s http://localhost:%d -c 4 -p 8000 -a 0.0.0.0" % \
                  (self.libra_path, mint_key_path, 12000 + self.my_id)
            self.faucet_client = subprocess.Popen(cmd.split(" "), stdout=out_file, stderr=out_file)
        if self.is_client():
            validator_peer_id = (self.my_id - 1) % self.num_validators
            validator_host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id + 1)
            validator_port = 12000 + validator_peer_id + 1
            self._logger.info("Spawning client that connects to validator %s (host: %s, port %s)",
                              validator_peer_id, validator_host, validator_port)
            self.diem_client = jsonrpc.Client("http://%s:%d" % (validator_host, validator_port))

    @experiment_callback
    def create_accounts(self):
        if not self.is_client():
            return

        self._logger.info("Creating accounts...")
        self.sender_account = LocalAccount.generate()
        self.receiver_account = LocalAccount.generate()

    @experiment_callback
    async def mint(self):
        if not self.is_client():
            return

        client_id = self.my_id - self.num_validators
        random_wait = (200 / self.num_clients) * (client_id - 1)

        await sleep(random_wait)

        faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)
        auth_key = self.sender_account.auth_key.hex()

        async with aiohttp.ClientSession() as session:
            url = "http://" + faucet_host + ":8000/?amount=%d&auth_key=%s&currency_code=XUS" % (10000000000, auth_key)
            await session.post(url)

        self._logger.info("Mint request performed with auth key %s!", auth_key)

    @staticmethod
    def create_transaction(sender, sender_account_sequence, script, currency):
        return diem_types.RawTransaction(
            sender=sender.account_address,
            sequence_number=sender_account_sequence,
            payload=diem_types.TransactionPayload__Script(script),
            max_gas_amount=1_000_000,
            gas_unit_price=0,
            gas_currency_code=currency,
            expiration_timestamp_secs=int(time.time()) + 30,
            chain_id=chain_ids.TESTING,
        )

    @experiment_callback
    def transfer(self):
        amount = 1_000_000

        script = stdlib.encode_peer_to_peer_with_metadata_script(
            currency=utils.currency_code(testnet.TEST_CURRENCY_CODE),
            payee=self.receiver_account.account_address,
            amount=amount,
            metadata=b"",  # no requirement for metadata and metadata signature
            metadata_signature=b"",
        )
        txn = LibraModule.create_transaction(self.sender_account, self.current_seq_num, script,
                                             testnet.TEST_CURRENCY_CODE)

        signed_txn = self.sender_account.sign(txn)
        self.diem_client.submit(signed_txn)

        submit_time = int(round(time.time() * 1000))
        self.tx_info[self.current_seq_num] = (submit_time, -1)
        self.current_seq_num += 1

    @experiment_callback
    def start_monitor(self):
        if not self.is_client():
            return

        self.monitor_lc = run_task(self.monitor, interval=0.1)

    def monitor(self):
        """
        Monitor the transactions.
        """
        request_time = int(round(time.time() * 1000))

        ledger_seq_num = self.diem_client.get_account_sequence(self.sender_account.account_address)
        if ledger_seq_num == 0:
            self._logger.warning("Empty account blob!")
            return

        for seq_num in range(self.last_tx_confirmed + 1, ledger_seq_num):
            if seq_num == -1:
                continue
            self.tx_info[seq_num] = (self.tx_info[seq_num][0], request_time)

        self.last_tx_confirmed = ledger_seq_num - 1

    @experiment_callback
    def stop_monitor(self):
        if not self.is_client():
            return

        self.monitor_lc.cancel()

    @experiment_callback
    def write_stats(self):
        if not self.is_client():
            # Write the disk usage of the data directory
            with open("disk_usage.txt", "w") as disk_out_file:
                data_dir = os.path.join("/tmp", "diem_data_%d" % self.num_validators, "%d" % (self.my_id - 1))
                dir_size = ExperimentModule.get_dir_size(data_dir)
                disk_out_file.write("%d" % dir_size)

            return

        # Write transaction data
        with open("transactions.txt", "w") as tx_file:
            for tx_num, tx_info in self.tx_info.items():
                tx_file.write("%d,%d,%d\n" % (tx_num, tx_info[0], tx_info[1]))

        # Write account balances
        rpc_account = self.diem_client.get_account(self.sender_account.account_address)
        balances = rpc_account.balances
        self._logger.info("Sender account balances: %s", balances)

    @experiment_callback
    async def stop(self):
        print("Stopping Diem...")
        if self.libra_validator_process:
            self.libra_validator_process.terminate()
        if self.faucet_client:
            self.faucet_client.terminate()

        loop = get_event_loop()
        loop.stop()
