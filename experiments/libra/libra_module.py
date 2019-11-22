import os
import shutil
import subprocess
import sys
import time

import pexpect as pexpect
import six
import toml

import libra
from libra import Client, RawTransaction, SignedTransaction, TransactionError
from libra.proto.admission_control_pb2 import SubmitTransactionRequest
from libra.transaction import Script, TransactionPayload

from twisted.internet import reactor
from twisted.internet.defer import fail
from twisted.internet.task import deferLater, LoopingCall
from twisted.web import server, http
from twisted.web.client import readBody, WebClientContextFactory, Agent
from twisted.web.http_headers import Headers

from experiments.libra.faucet_endpoint import FaucetEndpoint
from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import static_module


def http_request(uri, method):
    """
    Performs a HTTP request
    :param uri: The URL to perform a HTTP request to
    :return: A deferred firing the body of the response.
    :raises HttpError: When the HTTP response code is not OK (i.e. not the HTTP Code 200)
    """
    def _on_response(response):
        if response.code == http.OK:
            return readBody(response)
        raise Exception(response)

    try:
        uri = six.ensure_binary(uri)
    except AttributeError:
        pass
    try:
        contextFactory = WebClientContextFactory()
        agent = Agent(reactor, contextFactory)
        headers = Headers({'User-Agent': ['Tribler 1.2.3']})
        deferred = agent.request(method, uri, headers, None)
        deferred.addCallback(_on_response)
        return deferred
    except:
        return fail()


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
        cmd = "%s/target/release/libra-config -b %s/config/data/configs/node.config.toml -m %s/terraform/validator-sets/dev/mint.key -o %s/das_config -n %d" % \
              (self.libra_path, self.libra_path, self.libra_path, self.libra_path, self.num_validators)
        os.system(cmd)

    @experiment_callback
    def init_config(self):
        """
        Initialize the configuration. In particular, make sure the addresses of the seed nodes are correctly set.
        """
        my_peer_id = self.experiment.scenario_runner._peernumber
        self.validator_id = my_peer_id - 1
        if not self.is_client():
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id, "node.config.toml"), "r") as node_config_file:
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
                node_config["execution"]["genesis_file_location"] = os.path.join(self.libra_path, "terraform", "validator-sets", "dev", "genesis.blob")

                # Fix data directories
                node_config["base"]["data_dir_path"] = os.getcwd()
                node_config["storage"]["dir"] = os.path.join(os.getcwd(), "libradb", "db")

            # Write the updated node configuration
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id, "node.config.toml"), "w") as node_config_file:
                node_config_file.write(toml.dumps(node_config))

            # Update the seed configuration
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id, "%s.seed_peers.config.toml" % self.validator_peer_id), "r") as seed_peers_file:
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
            with open(os.path.join(self.libra_path, "das_config", "%d" % self.validator_id, "%s.seed_peers.config.toml" % self.validator_peer_id), "w") as seed_peers_file:
                seed_peers_file.write(toml.dumps(seed_peers_config))

    @experiment_callback
    def start_libra_validator(self):
        # Read the config
        my_peer_id = self.experiment.scenario_runner._peernumber
        if self.is_client():
            return

        # Start a validator
        my_libra_id = self.validator_ids[my_peer_id - 1]

        self._logger.info("Starting libra validator with id %s...", my_libra_id)
        self.libra_validator_process = subprocess.Popen(['/home/pouwelse/libra/target/release/libra-node -f %s > %s 2>&1' %
                                                         ('/home/pouwelse/libra/das_config/%d/node.config.toml' % (my_peer_id - 1),
                                                          os.path.join(os.getcwd(), 'libra_output.log'))], shell=True)

    @experiment_callback
    def start_libra_client(self):
        my_peer_id = self.experiment.scenario_runner._peernumber
        validator_peer_id = (my_peer_id - 1) % self.num_validators

        with open(os.path.join(self.libra_path, "das_config", "%d" % validator_peer_id, "node.config.toml"), "r") as validator_config_file:
            content = validator_config_file.read()
            validator_config = toml.loads(content)

        port = validator_config["admission_control"]["admission_control_service_port"]
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id + 1)

        # Get the faucet host
        faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)

        if my_peer_id == 1:
            # Start the minting service
            cmd = "/home/pouwelse/libra/target/release/client " \
                  "--host %s " \
                  "--port %s " \
                  "--validator-set-file /home/pouwelse/libra/das_config/%d/consensus_peers.config.toml " \
                  "-m /home/pouwelse/libra/terraform/validator-sets/dev/mint.key" % (host, port, validator_peer_id)

            self.faucet_client = pexpect.spawn(cmd)
            self.faucet_client.logfile = sys.stdout.buffer
            self.faucet_client.expect("Please, input commands", timeout=3)

            # Also start the HTTP API for the faucet service
            self._logger.info("Starting faucet HTTP API...")
            faucet_endpoint = FaucetEndpoint(self.faucet_client)
            site = server.Site(resource=faucet_endpoint)
            self.faucet_service = reactor.listenTCP(8000, site, interface="0.0.0.0")

        if self.is_client():
            self._logger.info("Spawning client that connects to validator %s (host: %s, port %s)", validator_peer_id, host, port)
            self.libra_client = Client.new(host, port, os.path.join(self.libra_path, "das_config", "%d" % validator_peer_id,"consensus_peers.config.toml"))
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
    def mint(self):
        if not self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        client_id = my_peer_id - self.num_validators
        random_wait = 10 / self.num_clients * client_id

        def perform_mint_request():
            faucet_host, _ = self.experiment.get_peer_ip_port_by_id(1)
            address = self.wallet.accounts[0].address.hex()
            deferred = http_request("http://" + faucet_host + ":8000/?amount=%d&address=%s" % (1000000, address), b'POST')
            print("Mint request performed!")

        deferLater(reactor, random_wait, perform_mint_request)

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

        self.monitor_lc = LoopingCall(self.monitor)
        self.monitor_lc.start(0.1)

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

        self.monitor_lc.stop()

    @experiment_callback
    def write_tx_stats(self):
        # Write transaction data
        with open("transactions.txt", "w") as tx_file:
            for tx_num, tx_info in self.tx_info.items():
                tx_file.write("%d,%d,%d\n" % (tx_num, tx_info[0], tx_info[1]))

    @experiment_callback
    def stop(self):
        print("Stopping Libra...")
        if self.libra_validator_process:
            self.libra_validator_process.kill()
        if self.faucet_process:
            self.faucet_process.kill()
        reactor.stop()
