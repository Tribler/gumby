import os
import subprocess
import sys
import time
from threading import Thread

from urllib.parse import quote_plus

from datetime import datetime

import requests

import treq

from stellar_base import Keypair, Horizon
from stellar_base.builder import Builder
from stellar_base.transaction_envelope import TransactionEnvelope

from twisted.internet import reactor

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule
from gumby.modules.experiment_module import static_module


class AccountStatus(object):
    IDLE = 0
    REQ_PENDING = 1


@static_module
class StellarModule(BlockchainModule):

    def __init__(self, experiment):
        super(StellarModule, self).__init__(experiment)
        self.db_path = None
        self.postgres_process = None
        self.validator_process = None
        self.horizon_process = None
        self.experiment.message_callback = self

        self.num_accounts_per_client = int(os.environ["ACCOUNTS_PER_CLIENT"])

        self.sender_keypairs = [None] * self.num_accounts_per_client
        self.receiver_keypair = None
        self.sequence_numbers = [25769803776] * self.num_accounts_per_client
        self.account_status = [AccountStatus.IDLE] * self.num_accounts_per_client
        self.current_tx_num = 0
        self.tx_submit_times = {}

        # Make sure our postgres can be found
        sys.path.append("/home/pouwelse/postgres/bin")

    def on_all_vars_received(self):
        super(StellarModule, self).on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    def on_message(self, from_id, msg_type, msg):
        self._logger.info("Received message with type %s from peer %d", msg_type, from_id)
        if msg_type.startswith(b"send_account_seed"):
            account_nr = int(msg_type.split(b"_")[-1])
            self.sender_keypairs[account_nr] = Keypair.from_seed(msg)
            self._logger.info("Address of account %d: %s" % (account_nr, self.sender_keypairs[account_nr].address().decode()))
        elif msg_type == b"receive_account_seed":
            self.receiver_keypair = Keypair.from_seed(msg)

    def is_responsible_validator(self):
        """
        Return whether this validator is the responsible validator to setup/init databases on this machine.
        This can only be conducted by a single process.
        """
        if self.is_client():
            return False

        my_peer_id = self.experiment.scenario_runner._peernumber
        my_host, _ = self.experiment.get_peer_ip_port_by_id(my_peer_id)

        is_responsible = True
        for peer_id in self.experiment.all_vars.keys():
            if self.experiment.all_vars[peer_id]['host'] == my_host and int(peer_id) < my_peer_id:
                is_responsible = False
                break

        return is_responsible

    @experiment_callback
    def init_db(self):
        """
        Start the postgres daemon.
        """
        if self.is_client() or not self.is_responsible_validator():
            return

        peer_id = self.experiment.scenario_runner._peernumber
        ip, _ = self.experiment.get_peer_ip_port_by_id(peer_id)

        self.db_path = os.path.join(os.environ["WORKSPACE"], "postgres", ip)
        os.makedirs(self.db_path)

        os.system("/home/pouwelse/postgres/bin/initdb %s" % self.db_path)

    @experiment_callback
    def start_db(self):
        if self.is_client() or not self.is_responsible_validator():
            return

        os.environ["PGDATA"] = self.db_path
        cmd = "/home/pouwelse/postgres/bin/pg_ctl start"
        self.postgres_process = subprocess.Popen([cmd], shell=True)

    @experiment_callback
    def setup_db(self):
        if self.is_client() or not self.is_responsible_validator():
            return

        # Create users and table
        cmd = "CREATE USER tribler WITH PASSWORD 'tribler';"
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

        cmd = "ALTER USER tribler WITH SUPERUSER;"
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

    @experiment_callback
    def create_db(self):
        if self.is_client():
            return

        peer_id = self.experiment.scenario_runner._peernumber

        cmd = "CREATE DATABASE stellar_%d_db;" % peer_id
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

        cmd = "GRANT ALL PRIVILEGES ON DATABASE stellar_%d_db TO tribler;" % peer_id
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

        cmd = "CREATE DATABASE stellar_horizon_%d_db;" % peer_id
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

        cmd = "GRANT ALL PRIVILEGES ON DATABASE stellar_horizon_%d_db TO tribler;" % peer_id
        os.system('/home/pouwelse/postgres/bin/psql postgres -c "%s"' % cmd)

    @experiment_callback
    def init_config(self):
        """
        Initialize the Stellar configurations.
        """
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        node_name = "valnode%d" % my_peer_id

        # Read the keys
        keys = []
        with open("/home/pouwelse/stellar-core/keys.txt", "r") as keys_file:
            for line in keys_file.readlines():
                line = line.strip()
                seed, pub_key = line.split(" ")
                keys.append((seed, pub_key))

        # Make the validators info
        validators_string = ""
        for validator_index in range(self.num_validators):
            if validator_index + 1 == my_peer_id:
                continue
            validator_host, _ = self.experiment.get_peer_ip_port_by_id(validator_index + 1)
            validators_string += """[[VALIDATORS]]
NAME="valnode%d"
HOME_DOMAIN="dev"
PUBLIC_KEY="%s"
ADDRESS="%s:%d"

""" % (validator_index + 1, keys[validator_index][1], validator_host, 14000 + validator_index + 1)

        with open("/home/pouwelse/stellar-core/stellar-core-template.cfg", "r") as template_file:
            template_content = template_file.read()

        template_content = template_content.replace("<HTTP_PORT>", str(11000 + my_peer_id))
        template_content = template_content.replace("<NODE_SEED>", keys[my_peer_id - 1][0])
        template_content = template_content.replace("<NODE_NAME>", node_name)
        template_content = template_content.replace("<DB_NAME>", "stellar_%d_db" % my_peer_id)
        template_content = template_content.replace("<PEER_PORT>", str(14000 + my_peer_id))
        template_content = template_content.replace("<VALIDATORS>", validators_string)

        with open("stellar-core.cfg", "w") as config_file:
            config_file.write(template_content)

    @experiment_callback
    def init_validators(self):
        """
        Initialize all validators.
        """
        if self.is_client():
            return

        cmd = "/home/pouwelse/stellar-core/stellar-core new-db"
        os.system(cmd)  # Blocking execution

        cmd = "/home/pouwelse/stellar-core/stellar-core force-scp"
        os.system(cmd)  # Blocking execution

    @experiment_callback
    def start_validators(self):
        """
        Start all Stellar validators.
        """
        if self.is_client():
            return

        cmd = "/home/pouwelse/stellar-core/stellar-core run 2>&1"
        self.validator_process = subprocess.Popen([cmd], shell=True, stdout=subprocess.DEVNULL)

    @experiment_callback
    def start_horizon(self):
        """
        Start the horizon interface.
        """
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        db_name = "stellar_%d_db" % my_peer_id
        horizon_db_name = "stellar_horizon_%d_db" % my_peer_id
        cmd = '/home/pouwelse/horizon/horizon --port %d ' \
              '--ingest ' \
              '--db-url "postgresql://tribler:tribler@localhost:5432/%s?sslmode=disable" ' \
              '--stellar-core-db-url "postgresql://tribler:tribler@localhost:5432/%s?sslmode=disable" ' \
              '--stellar-core-url "http://127.0.0.1:%d" ' \
              '--network-passphrase="Standalone Pramati Network ; Oct 2018" ' \
              '--apply-migrations > horizon.out ' \
              '--ingest-failed-transactions=true ' \
              '--log-level=info ' \
              '--per-hour-rate-limit 0 2>&1' % (19000 + my_peer_id, horizon_db_name, db_name, 11000 + my_peer_id)

        self.horizon_process = subprocess.Popen([cmd], shell=True)

    @experiment_callback
    def upgrade_tx_set_size(self):
        if self.is_client():
            return

        self._logger.info("Upgrading tx size limit")

        my_peer_id = self.experiment.scenario_runner._peernumber
        response = requests.get("http://127.0.0.1:%d/upgrades?mode=set&upgradetime=1970-01-01T00:00:00Z&maxtxsize=10000" % (11000 + my_peer_id,))
        self._logger.info("Response: %s", response.text)

    @experiment_callback
    def create_accounts(self):
        """
        Create accounts for every client. Send the secret seeds to the clients.
        """
        self._logger.info("Creating accounts...")

        my_peer_id = self.experiment.scenario_runner._peernumber
        validator_peer_id = ((my_peer_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)
        horizon_uri = "http://%s:%d" % (host, 19000 + validator_peer_id)

        def on_content(content):
            self._logger.info("Create accounts request failed with response: %s", content)

        def on_response(response):
            if response.code != 200:
                treq.text_content(response).addCallback(on_content)
            else:
                self._logger.error("Create accounts request successful!")

        def append_create_account_op(builder, receiver_pub_key, amount):
            builder.append_create_account_op(receiver_pub_key, amount)
            if len(builder.ops) == 100:
                self._logger.info("Sending create transaction ops...")
                builder.sign()
                treq.post(horizon_uri + "/transactions/", data={"tx": builder.gen_xdr()}).addCallback(on_response)
                builder = builder.next_builder()

            return builder

        builder = Builder(secret="SDJ5AQWLIAYT22TCYSKOQALI3SNUMPAR63SEL73ASALDP6PYDN54FARM",
                          horizon_uri=horizon_uri,
                          network="Standalone Pramati Network ; Oct 2018")

        for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
            receiver_keypair = Keypair.random()
            receiver_pub_key = receiver_keypair.address().decode()
            builder = append_create_account_op(builder, receiver_pub_key, "10000000")
            self.experiment.send_message(client_index, b"receive_account_seed", receiver_keypair.seed())

            # Create the sender accounts
            for account_ind in range(self.num_accounts_per_client):
                sender_keypair = Keypair.random()
                sender_pub_key = sender_keypair.address().decode()
                builder = append_create_account_op(builder, sender_pub_key, "10000000")
                self.experiment.send_message(client_index, b"send_account_seed_%d" % account_ind, sender_keypair.seed())

        if len(builder.ops):
            self._logger.info("Sending create transaction ops...")
            builder.sign()
            treq.post(horizon_uri + "/transactions/", data={"tx": builder.gen_xdr()})

    @experiment_callback
    def get_initial_sq_num(self):
        if not self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        validator_peer_id = ((my_peer_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        builder = Builder(secret=self.sender_keypairs[0].seed(),
                          horizon_uri="http://%s:%d" % (host, 19000 + validator_peer_id),
                          network="Standalone Pramati Network ; Oct 2018",
                          fee=100)

        # Set the sequence number for all accounts
        for account_ind in range(self.num_accounts_per_client):
            self.sequence_numbers[account_ind] = builder.sequence

    @experiment_callback
    def transfer(self):
        if not self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        validator_peer_id = ((my_peer_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        # Get an idle account
        source_account_nr = None
        for account_ind in range(self.num_accounts_per_client):
            if self.account_status[account_ind] == AccountStatus.IDLE:
                source_account_nr = account_ind
                self.account_status[account_ind] = AccountStatus.REQ_PENDING
                break

        if source_account_nr is None:
            self._logger.info("Could not find an idle account for transfer!")
            return

        self._logger.info("Will transfer from account %d, sq num: %d", source_account_nr, self.sequence_numbers[source_account_nr])

        builder = Builder(secret=self.sender_keypairs[source_account_nr].seed(),
                          horizon_uri="http://%s:%d" % (host, 19000 + validator_peer_id),
                          network="Standalone Pramati Network ; Oct 2018",
                          sequence=self.sequence_numbers[source_account_nr],
                          fee=100)
        builder.horizon.request_timeout = 60

        builder.append_payment_op(self.receiver_keypair.address(), '100', 'XLM')
        builder.sign()

        self._logger.info("Submitting transaction with id %d", self.sequence_numbers[source_account_nr])

        def send_transaction(tx, seq_num, account_nr):
            tx_id = self.sender_keypairs[source_account_nr].address().decode() + "." + "%d" % seq_num
            submit_time = int(round(time.time() * 1000))
            response = requests.get("http://%s:%d/tx?blob=%s" % (host, 11000 + validator_peer_id, quote_plus(tx.decode())))
            self.account_status[account_nr] = AccountStatus.IDLE
            self._logger.info("Received response for transaction with account %d and id %d: %s", account_nr, seq_num, response.text)
            if response.status_code != 200 or response.json()["status"] != "PENDING":
                # Restore seq num
                new_seq_num = builder.get_sequence()
                self.sequence_numbers[account_nr] = new_seq_num
                self._logger.info("Reset sequence number of account %d from %d to %d", account_nr, seq_num, new_seq_num)
            elif response.json()["status"] == "PENDING":
                self.tx_submit_times[tx_id] = submit_time

        t = Thread(target=send_transaction, args=(builder.gen_xdr(), self.sequence_numbers[source_account_nr], source_account_nr))
        t.daemon = True
        t.start()

        self.sequence_numbers[source_account_nr] += 1
        self.current_tx_num += 1

    @experiment_callback
    def write_submit_times(self):
        if not self.is_client():
            return

        with open("tx_submit_times.txt", "w") as tx_submit_times_file:
            for tx_id, submit_time in self.tx_submit_times.items():
                tx_submit_times_file.write("%s,%d\n" % (tx_id, submit_time))

    @experiment_callback
    def print_metrics(self):
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        horizon = Horizon("http://127.0.0.1:%d" % (19000 + my_peer_id),)
        metrics = horizon.metrics()
        print("Horizon metrics: %s" % metrics)

    @experiment_callback
    def print_ledgers(self):
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        horizon = Horizon("http://127.0.0.1:%d" % (19000 + my_peer_id), )
        ledgers = horizon.ledgers(limit=100)
        print("Ledgers: %s" % ledgers)

    @experiment_callback
    def parse_ledgers(self):
        self._logger.info("Parsing ledgers...")
        my_peer_id = self.experiment.scenario_runner._peernumber
        horizon_url = "http://127.0.0.1:%d" % (19000 + my_peer_id)
        horizon = Horizon(horizon_url)
        ledgers = horizon.ledgers(limit=100)
        tx_times = {}
        for ledger_info in ledgers["_embedded"]["records"]:
            ledger_sq = ledger_info["sequence"]
            self._logger.info("Parsing ledger %d...", ledger_sq)
            close_time = datetime.fromisoformat(ledger_info["closed_at"].replace("Z", "+00:00")).timestamp() * 1000

            # Get the transactions in this ledger
            transactions = horizon.ledger_transactions(ledger_sq, limit=200, include_failed=True)  # TODO chain requests
            while True:
                if not transactions["_embedded"]["records"]:
                    break

                for transaction in transactions["_embedded"]["records"]:
                    te = TransactionEnvelope.from_xdr(transaction["envelope_xdr"])
                    tx_id = te.tx.source.decode() + "." + "%d" % (te.tx.sequence - 1)
                    tx_times[tx_id] = close_time

                response = requests.get(transactions["_links"]["next"]["href"])
                transactions = response.json()

        with open("tx_finalized_times.txt", "w") as tx_finalized_times_file:
            for tx_id, close_time in tx_times.items():
                tx_finalized_times_file.write("%s,%d\n" % (tx_id, close_time))

    @experiment_callback
    def stop(self):
        print("Stopping Stellar...")
        if self.postgres_process:
            self._logger.info("Killing postgres")
            self.postgres_process.kill()
        if self.validator_process:
            self._logger.info("Killing validator")
            self.validator_process.kill()
        if self.horizon_process:
            self._logger.info("Killing horizon")
            self.horizon_process.kill()
        reactor.stop()
