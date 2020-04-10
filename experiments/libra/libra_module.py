import decimal
import os
import re
import shutil
import subprocess
import sys
import time
from asyncio import sleep, get_event_loop

import aiohttp
from aiohttp import web

import pexpect

import toml

import libra
from libra import Client, RawTransaction, SignedTransaction, TransactionError
from libra.proto.admission_control_pb2 import SubmitTransactionRequest
from libra.transaction import Script, TransactionPayload

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import static_module
from gumby.util import run_task


MAX_MINT = 10 ** 19  # 10 trillion libras


@static_module
class LibraModule(BlockchainModule):

    def __init__(self, experiment):
        super(LibraModule, self).__init__(experiment)
        self.libra_validator_process = None
        self.faucet_process = None
        self.libra_client = None
        self.faucet_client = None
        self.faucet_service = None
        self.libra_path = "/home/pouwelse/libra"
        self.validator_config = None
        self.validator_id = None
        self.validator_peer_id = None
        self.validator_ids = None
        self.wallet = None
        self.tx_info = {}
        self.last_tx_confirmed = -1
        self.site = None

        self.monitor_lc = None
        self.current_seq_num = 0

    def on_all_vars_received(self):
        super(LibraModule, self).on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    @experiment_callback
    def generate_config(self):
        """
        Generate the initial configuration files.
        """
        self._logger.info("Generating config...")

        # Step 1: remove configuration from previous run
        shutil.rmtree("%s/das_config" % self.libra_path, ignore_errors=True)

        # Step 2: generate new configuration
        cmd = "%s/target/release/libra-config -b %s/config/data/configs/node.config.toml " \
              "-m %s/terraform/validator-sets/dev/mint.key -o %s/das_config -n %d" % \
              (self.libra_path, self.libra_path, self.libra_path, self.libra_path, self.num_validators)
        os.system(cmd)

    @experiment_callback
    def init_config(self):
        """
        Initialize the configuration. In particular, make sure the addresses of the seed nodes are correctly set.
        """
        self.validator_id = self.my_id - 1
        if not self.is_client():
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id,
                                   "node.config.toml"), "r") as node_config_file:
                content = node_config_file.read()
                node_config = toml.loads(content)
                self.validator_peer_id = node_config["networks"][0]["peer_id"]

                listen_address = node_config["networks"][0]["listen_address"]
                listen_address = listen_address.replace("ip6", "ip4")
                listen_address = listen_address.replace("::1", "0.0.0.0")
                node_config["networks"][0]["listen_address"] = listen_address

                advertised_address = node_config["networks"][0]["advertised_address"]
                advertised_address = advertised_address.replace("ip6", "ip4")
                advertised_address = advertised_address.replace("::1", "0.0.0.0")
                node_config["networks"][0]["advertised_address"] = advertised_address

                node_config["admission_control"]["address"] = "0.0.0.0"
                node_config["mempool"]["capacity_per_user"] = 10000
                node_config["consensus"]["max_block_size"] = 10000
                node_config["execution"]["genesis_file_location"] = os.path.join(self.libra_path, "terraform",
                                                                                 "validator-sets", "dev",
                                                                                 "genesis.blob")

                # Fix data directories
                node_config["base"]["data_dir_path"] = os.getcwd()
                node_config["storage"]["dir"] = os.path.join(os.getcwd(), "libradb", "db")

            # Write the updated node configuration
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id,
                                   "node.config.toml"), "w") as node_config_file:
                node_config_file.write(toml.dumps(node_config))

            # Update the seed configuration
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id,
                                   "%s.seed_peers.config.toml" % self.validator_peer_id), "r") as seed_peers_file:
                content = seed_peers_file.read()
                seed_peers_config = toml.loads(content)
                self.validator_ids = sorted(list(seed_peers_config["seed_peers"].keys()))

            # Adjust
            for validator_index in range(len(self.validator_ids)):
                ip, _ = self.experiment.get_peer_ip_port_by_id(validator_index + 1)
                validator_id = self.validator_ids[validator_index]

                current_host = seed_peers_config["seed_peers"][validator_id][0]
                parts = current_host.split("/")
                listen_port = parts[4]

                seed_peers_config["seed_peers"][validator_id][0] = "/ip4/%s/tcp/%s" % (ip, listen_port)

            # Write
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id,
                                   "%s.seed_peers.config.toml" % self.validator_peer_id), "w") as seed_peers_file:
                seed_peers_file.write(toml.dumps(seed_peers_config))

    @experiment_callback
    def start_libra_validator(self):
        # Read the config
        if self.is_client():
            return

        # Start a validator
        my_libra_id = self.validator_ids[self.my_id - 1]

        self._logger.info("Starting libra validator with id %s...", my_libra_id)

        cmd = '/home/pouwelse/libra/target/release/libra-node -f %s > %s 2>&1' \
              % ('/home/pouwelse/libra/das_config/%d/node.config.toml' %
                 (self.my_id - 1), os.path.join(os.getcwd(), 'libra_output.log'))
        self.libra_validator_process = subprocess.Popen([cmd], shell=True)

    async def on_mint_request(self, request):
        address = request.rel_url.query['address']
        self._logger.info("Received mint request for address %s", address)
        if re.match('^[a-f0-9]{64}$', address) is None:
            return web.Response(text="Malformed address", status=400)

        try:
            amount = decimal.Decimal(request.rel_url.query['amount'])
        except decimal.InvalidOperation:
            return web.Response(text="Bad amount", status=400)

        if amount > MAX_MINT:
            return web.Response(text="Exceeded max amount of {}".format(MAX_MINT / (10 ** 6)), status=400)

        self.faucet_client.sendline("a m {} {}".format(address, amount / (10 ** 6)))
        self.faucet_client.expect("Mint request submitted", timeout=2)

        return web.Response(text="done")

    @experiment_callback
    async def start_libra_client(self):
        validator_peer_id = (self.my_id - 1) % self.num_validators

        with open(os.path.join(self.libra_path, "das_config", "%d" % validator_peer_id, "node.config.toml"), "r") \
                as validator_config_file:
            content = validator_config_file.read()
            validator_config = toml.loads(content)

        port = validator_config["admission_control"]["admission_control_service_port"]
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id + 1)

        # Get the faucet host
        faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)

        if self.my_id == 1:
            # Start the minting service
            cmd = "/home/pouwelse/libra/target/release/client " \
                  "--host %s " \
                  "--port %s " \
                  "--validator-set-file /home/pouwelse/libra/das_config/%d/consensus_peers.config.toml " \
                  "-m /home/pouwelse/libra/terraform/validator-sets/dev/mint.key" % (host, port, validator_peer_id)

            self.faucet_client = pexpect.spawn(cmd)
            self.faucet_client.delaybeforesend = 0.1
            self.faucet_client.logfile = sys.stdout.buffer
            self.faucet_client.expect("Please, input commands", timeout=3)

            # Also start the HTTP API for the faucet service
            self._logger.info("Starting faucet HTTP API...")
            app = web.Application()
            app.add_routes([web.get('/', self.on_mint_request)])

            runner = web.AppRunner(app, access_log=None)
            await runner.setup()
            # If localhost is used as hostname, it will randomly either use 127.0.0.1 or ::1
            self.site = web.TCPSite(runner, port=8000)
            await self.site.start()

        if self.is_client():
            self._logger.info("Spawning client that connects to validator %s (host: %s, port %s)",
                              validator_peer_id, host, port)
            self.libra_client = Client.new(host, port,
                                           os.path.join(self.libra_path, "das_config", "%d" % validator_peer_id,
                                                        "consensus_peers.config.toml"))
            self.libra_client.faucet_host = faucet_host + ":8000"

    @experiment_callback
    def create_accounts(self):
        if not self.is_client():
            return

        self._logger.info("Creating accounts...")
        self.wallet = libra.WalletLibrary.new()
        self.wallet.new_account()
        self.wallet.new_account()

    @experiment_callback
    async def mint(self):
        if not self.is_client():
            return

        client_id = self.my_id - self.num_validators
        random_wait = 10 / self.num_clients * client_id

        await sleep(random_wait)

        faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)
        address = self.wallet.accounts[0].address.hex()

        async with aiohttp.ClientSession() as session:
            url = "http://" + faucet_host + ":8000/?amount=%d&address=%s" % (1000000, address)
            await session.get(url)

        print("Mint request performed!")

    @experiment_callback
    def print_balance(self, account_nr):
        if not self.is_client():
            return

        address = self.wallet.accounts[int(account_nr)].address
        print(self.libra_client.get_balance(address))

    @experiment_callback
    def transfer(self):
        receiver_address = self.wallet.accounts[1].address
        sender_account = self.wallet.accounts[0]

        script = Script.gen_transfer_script(receiver_address, 100)
        payload = TransactionPayload('Script', script)
        raw_tx = RawTransaction.new_tx(sender_account.address, self.current_seq_num, payload, 140_000, 0, 100)
        signed_txn = SignedTransaction.gen_from_raw_txn(raw_tx, sender_account)
        request = SubmitTransactionRequest()
        request.transaction.txn_bytes = signed_txn.serialize()
        submit_time = int(round(time.time() * 1000))

        try:
            self.libra_client.submit_transaction(request, raw_tx, False)
        except TransactionError:
            self._logger.exception("Failed to submit transaction to validator!")

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

        ledger_seq_num = self.libra_client.get_sequence_number(self.wallet.accounts[0].address)
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
    def write_tx_stats(self):
        # Write transaction data
        with open("transactions.txt", "w") as tx_file:
            for tx_num, tx_info in self.tx_info.items():
                tx_file.write("%d,%d,%d\n" % (tx_num, tx_info[0], tx_info[1]))

    @experiment_callback
    async def stop(self):
        print("Stopping Libra...")
        if self.libra_validator_process:
            self.libra_validator_process.kill()
        if self.faucet_process:
            self.faucet_process.kill()
        if self.site:
            await self.site.stop()

        loop = get_event_loop()
        loop.stop()

        # Delete the postgres directory
        shutil.rmtree("libradb", ignore_errors=True)
