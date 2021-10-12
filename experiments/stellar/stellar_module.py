import os
import random
import shlex
import shutil

from asyncio import get_event_loop, sleep
from threading import Thread
import requests
import subprocess
import time

from urllib.parse import quote_plus

from datetime import datetime

from stellar_sdk import Keypair, TransactionBuilder, AiohttpClient, Server, Account, TransactionEnvelope
from stellar_sdk.exceptions import NotFoundError

from gumby.experiment import experiment_callback
from gumby.modules.blockchain_module import BlockchainModule


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
        self.current_tx_num = 0
        self.tx_submit_times = {}
        self.current_account_nr = 0
        self.root_seq_num = 0

    def on_all_vars_received(self):
        super(StellarModule, self).on_all_vars_received()
        self.transactions_manager.transfer = self.transfer

    def on_message(self, from_id, msg_type, msg):
        self._logger.info("Received message with type %s from peer %d", msg_type, from_id)
        if msg_type.startswith(b"send_account_seed"):
            account_nr = int(msg_type.split(b"_")[-1])
            self.sender_keypairs[account_nr] = Keypair.from_secret(msg)
            self._logger.info("Address of account %d: %s", account_nr, self.sender_keypairs[account_nr].public_key)
        elif msg_type == b"receive_account_seed":
            self.receiver_keypair = Keypair.from_secret(msg)

    @experiment_callback
    def init_db(self):
        """
        Start the postgres daemon.
        """
        if self.is_client() or not self.is_responsible_validator():
            return

        ip, _ = self.experiment.get_peer_ip_port_by_id(self.my_id)

        self.db_path = os.path.join("/tmp", "postgres-data", ip)
        shutil.rmtree(self.db_path, ignore_errors=True)
        os.makedirs(self.db_path, exist_ok=True)

        os.system("/usr/lib/postgresql/11/bin/initdb %s > postgres.out" % self.db_path)

    @experiment_callback
    def start_db(self):
        if self.is_client() or not self.is_responsible_validator():
            return

        os.environ["PGDATA"] = self.db_path
        cmd = "/usr/lib/postgresql/11/bin/pg_ctl start"
        out_file = open("postgres.out", "w")
        self.postgres_process = subprocess.Popen(cmd.split(" "), stdout=out_file, stderr=out_file)

    @experiment_callback
    def setup_db(self):
        if self.is_client() or not self.is_responsible_validator():
            return

        # Create users and table
        cmd = "CREATE USER tribler WITH PASSWORD 'tribler';"
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

        cmd = "ALTER USER tribler WITH SUPERUSER;"
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

    @experiment_callback
    def create_db(self):
        if self.is_client():
            return

        cmd = "CREATE DATABASE stellar_%d_db;" % self.my_id
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

        cmd = "GRANT ALL PRIVILEGES ON DATABASE stellar_%d_db TO tribler;" % self.my_id
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

        cmd = "CREATE DATABASE stellar_horizon_%d_db;" % self.my_id
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

        cmd = "GRANT ALL PRIVILEGES ON DATABASE stellar_horizon_%d_db TO tribler;" % self.my_id
        os.system('/usr/lib/postgresql/11/bin/psql postgres -c "%s"' % cmd)

    @experiment_callback
    def init_config(self):
        """
        Initialize the Stellar configurations.
        """
        if self.is_client():
            return

        node_name = "valnode%d" % self.my_id

        # Read the keys
        keys = []
        with open("/home/martijn/stellar-core/keys.txt", "r") as keys_file:
            for line in keys_file.readlines():
                line = line.strip()
                seed, pub_key = line.split(" ")
                keys.append((seed, pub_key))

        # Make the validators info
        k = int(os.getenv('QUORUM', "11"))
        full_list = list(range(self.num_validators))
        quorum = random.sample(full_list, min(k, len(full_list)))

        # Make the validators info
        validators_string = ""
        for validator_index in quorum:
            if validator_index + 1 == self.my_id:
                continue
            validator_host, _ = self.experiment.get_peer_ip_port_by_id(validator_index + 1)
            validators_string += """[[VALIDATORS]]
NAME="valnode%d"
HOME_DOMAIN="dev"
PUBLIC_KEY="%s"
ADDRESS="%s:%d"

""" % (validator_index + 1, keys[validator_index][1], validator_host, 14000 + validator_index + 1)

        with open("/home/martijn/stellar-core/stellar-core-template.cfg", "r") as template_file:
            template_content = template_file.read()

        template_content = template_content.replace("<HTTP_PORT>", str(11000 + self.my_id))
        template_content = template_content.replace("<NODE_SEED>", keys[self.my_id - 1][0])
        template_content = template_content.replace("<NODE_NAME>", node_name)
        template_content = template_content.replace("<DB_NAME>", "stellar_%d_db" % self.my_id)
        template_content = template_content.replace("<PEER_PORT>", str(14000 + self.my_id))
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

        self._logger.info("Creating new DB...")

        cmd = "/home/martijn/stellar-core/stellar-core new-db"
        os.system(cmd)  # Blocking execution

        self._logger.info("Forcing SCP...")

        cmd = "/home/martijn/stellar-core/stellar-core force-scp"
        os.system(cmd)  # Blocking execution

        # Publish history
        if self.my_id == 1:
            self._logger.info("Publish a new history...")
            os.system("/home/martijn/stellar-core/stellar-core new-hist vs --conf=stellar-core.cfg > "
                      "publish_history.out")

    @experiment_callback
    async def start_validators(self):
        """
        Start all Stellar validators.
        """
        if self.is_client():
            return

        await sleep(random.random() * 3)

        cmd = "/home/martijn/stellar-core/stellar-core run"
        out_file = open("stellar.out", "w")
        self.validator_process = subprocess.Popen(cmd.split(" "), stdout=out_file, stderr=out_file)

    @experiment_callback
    def start_horizon(self):
        """
        Start the horizon interface.
        """
        if self.is_client():
            return

        self._logger.info("Starting Horizon...")

        db_name = "stellar_%d_db" % self.my_id
        horizon_db_name = "stellar_horizon_%d_db" % self.my_id
        args = '--port %d ' \
               '--ingest ' \
               '--db-url "postgresql://tribler:tribler@localhost:5432/%s?sslmode=disable" ' \
               '--stellar-core-db-url "postgresql://tribler:tribler@localhost:5432/%s?sslmode=disable" ' \
               '--stellar-core-url "http://127.0.0.1:%d" ' \
               '--network-passphrase="Standalone Pramati Network ; Oct 2018" ' \
               '--apply-migrations ' \
               '--log-level=info ' \
               '--history-archive-urls "file:///tmp/stellar-core/history/vs" ' \
               '--per-hour-rate-limit 0' % (19000 + self.my_id, horizon_db_name, db_name, 11000 + self.my_id)

        # First initialize Horizon with an empty genesis state
        cmd = '/home/martijn/gocode/bin/horizon expingest init-genesis-state %s > horizon_expingest.out 2>&1' % args
        os.system(cmd)

        # Now start Horizon
        cmd = '/home/martijn/gocode/bin/horizon %s' % args
        out_file = open("horizon.out", "w")
        self.horizon_process = subprocess.Popen(shlex.split(cmd), stdout=out_file, stderr=out_file)

    @experiment_callback
    async def upgrade_tx_set_size(self):
        if self.is_client():
            return

        upgrade_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        self._logger.info("Upgrading protocol version")
        response = requests.get(
            "http://127.0.0.1:%d/upgrades?mode=set&upgradetime=%s&protocolversion=15"
            % (11000 + self.my_id, upgrade_time))
        self._logger.info("Response to protocol upgrade: %s", response.status_code)

        await sleep(10)

        self._logger.info("Upgrading tx size limit")
        response = requests.get(
            "http://127.0.0.1:%d/upgrades?mode=set&upgradetime=%s&maxtxsize=10000&protocolversion=15"
            % (11000 + self.my_id, upgrade_time))
        self._logger.info("Response to tx size upgrade: %s", response.status_code)

        await sleep(10)

        self._logger.info("Fetching network upgrade settings")
        response = requests.get(
            "http://127.0.0.1:%d/upgrades?mode=get"
            % (11000 + self.my_id,))
        self._logger.info("Settings: %s", response.text)

    @experiment_callback
    async def create_accounts(self):
        """
        Create accounts for every client. Send the secret seeds to the clients.
        """
        self._logger.info("Creating accounts...")

        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)
        horizon_uri = "http://%s:%d" % (host, 19000 + validator_peer_id)

        root_keypair = Keypair.from_secret("SDJ5AQWLIAYT22TCYSKOQALI3SNUMPAR63SEL73ASALDP6PYDN54FARM")
        async with Server(horizon_url=horizon_uri, client=AiohttpClient()) as server:
            root_account = await server.load_account(root_keypair.public_key)
        self.root_seq_num = root_account.sequence
        self._logger.info("Setting root sequence number to %d", self.root_seq_num)

        builder = TransactionBuilder(
            source_account=root_account,
            network_passphrase="Standalone Pramati Network ; Oct 2018"
        )

        async def append_create_account_op(builder, root_keypair, receiver_pub_key, amount):
            builder.append_create_account_op(receiver_pub_key, amount, root_keypair.public_key)
            if len(builder.operations) == 100:
                self._logger.info("Sending create transaction ops...")
                tx = builder.build()
                tx.sign(root_keypair)
                response = requests.get("http://%s:%d/tx?blob=%s" % (host, 11000 + validator_peer_id,
                                                                     quote_plus(tx.to_xdr())))
                self._logger.info("Received response for create accounts request: %s", response.text)

                await sleep(2)

                self.root_seq_num += 1

                partial_root_acc = Account(root_keypair.public_key, self.root_seq_num)
                builder = TransactionBuilder(
                    source_account=partial_root_acc,
                    network_passphrase="Standalone Pramati Network ; Oct 2018"
                )

            return builder

        for client_index in range(self.num_validators + 1, self.num_validators + self.num_clients + 1):
            receiver_keypair = Keypair.random()
            builder = await append_create_account_op(builder, root_keypair, receiver_keypair.public_key, "10000000")
            self.experiment.send_message(client_index, b"receive_account_seed", receiver_keypair.secret.encode())

            # Create the sender accounts
            for account_ind in range(self.num_accounts_per_client):
                sender_keypair = Keypair.random()
                builder = await append_create_account_op(builder, root_keypair, sender_keypair.public_key, "10000000")
                self.experiment.send_message(client_index, b"send_account_seed_%d" % account_ind,
                                             sender_keypair.secret.encode())

        # Send the remaining operations
        if builder.operations:
            self._logger.info("Sending remaining create transaction ops...")
            tx = builder.build()
            tx.sign(root_keypair)
            response = requests.get("http://%s:%d/tx?blob=%s" % (host, 11000 + validator_peer_id,
                                                                 quote_plus(tx.to_xdr())))
            self._logger.info("Received response for create accounts request: %s", response.text)
            self.root_seq_num += 1

    @experiment_callback
    async def get_initial_sq_num(self):
        if not self.is_client():
            return

        self._logger.info("Getting initial sequence numbers...")

        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)
        horizon_uri = "http://%s:%d" % (host, 19000 + validator_peer_id)

        for account_ind in range(self.num_accounts_per_client):
            async with Server(horizon_url=horizon_uri, client=AiohttpClient()) as server:
                try:
                    sender_account = await server.load_account(self.sender_keypairs[account_ind])
                    # Set the sequence number for all accounts
                    self._logger.info("Sequence number for account %d: %d", account_ind, sender_account.sequence)
                    self.sequence_numbers[account_ind] = sender_account.sequence
                except NotFoundError:
                    self._logger.warning("Unable to fetch sequence number for account %d!", account_ind)

    @experiment_callback
    def transfer(self):
        if not self.is_client():
            return

        validator_peer_id = ((self.my_id - 1) % self.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(validator_peer_id)

        self._logger.info("Will transfer from account %d, sq num: %d",
                          self.current_account_nr, self.sequence_numbers[self.current_account_nr])

        sender_account = Account(self.sender_keypairs[self.current_account_nr].public_key,
                                 self.sequence_numbers[self.current_account_nr])
        builder = TransactionBuilder(
            source_account=sender_account,
            network_passphrase="Standalone Pramati Network ; Oct 2018"
        )

        builder.append_payment_op(self.receiver_keypair.public_key, '100', 'XLM')
        tx = builder.build()
        tx.sign(self.sender_keypairs[self.current_account_nr])

        self._logger.info("Submitting transaction with id %d", self.sequence_numbers[self.current_account_nr])

        def send_transaction(tx, seq_num, account_nr):
            tx_id = self.sender_keypairs[self.current_account_nr].public_key + "." + "%d" % seq_num
            submit_time = int(round(time.time() * 1000))
            response = requests.get("http://%s:%d/tx?blob=%s"
                                    % (host, 11000 + validator_peer_id, quote_plus(tx)))
            self._logger.info("Received response for transaction with account %d and id %d: %s",
                              account_nr, seq_num, response.text)
            if response.status_code != 200 or response.json()["status"] != "PENDING":
                # Restore seq num
                new_seq_num = builder.get_sequence()
                self.sequence_numbers[account_nr] = new_seq_num
                self._logger.info("Reset sequence number of account %d from %d to %d", account_nr, seq_num, new_seq_num)
            elif response.json()["status"] == "PENDING":
                self.tx_submit_times[tx_id] = submit_time

        t = Thread(target=send_transaction,
                   args=(tx.to_xdr(), self.sequence_numbers[self.current_account_nr], self.current_account_nr))
        t.daemon = True
        t.start()

        self.sequence_numbers[self.current_account_nr] += 1
        self.current_tx_num += 1
        self.current_account_nr = (self.current_account_nr + 1) % self.num_accounts_per_client

    @experiment_callback
    def write_stats(self):
        if not self.is_client():
            self._logger.info("Writing disk usage...")
            # Write the disk usage of the data directory
            cmd = "/usr/lib/postgresql/11/bin/psql postgres -c \"SELECT pg_database_size('stellar_%d_db')\" -t" % \
                  self.my_id
            proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
            out, _ = proc.communicate()
            disk_usage = int(out.strip())
            with open("disk_usage.txt", "w") as disk_out_file:
                disk_out_file.write("%d" % disk_usage)

            return

        with open("tx_submit_times.txt", "w") as tx_submit_times_file:
            for tx_id, submit_time in self.tx_submit_times.items():
                tx_submit_times_file.write("%s,%d\n" % (tx_id, submit_time))

    @experiment_callback
    def parse_ledgers(self):
        self._logger.info("Parsing ledgers...")
        horizon_url = "http://127.0.0.1:%d" % (19000 + self.my_id)

        response = requests.get(horizon_url + "/ledgers?limit=100")
        ledgers = response.json()
        tx_times = {}
        for ledger_info in ledgers["_embedded"]["records"]:
            ledger_sq = ledger_info["sequence"]
            self._logger.info("Parsing ledger %d...", ledger_sq)
            close_time = datetime.fromisoformat(ledger_info["closed_at"].replace("Z", "+00:00")).timestamp() * 1000

            # Get the transactions in this ledger
            transactions_url = "%s/ledgers/%d/transactions?limit=200&include_failed=True" % (horizon_url, ledger_sq)
            response = requests.get(transactions_url)
            transactions = response.json()
            while True:
                if not transactions["_embedded"]["records"]:
                    break

                for transaction in transactions["_embedded"]["records"]:
                    te = TransactionEnvelope.from_xdr(transaction["envelope_xdr"],
                                                      "Standalone Pramati Network ; Oct 2018")
                    tx_id = te.transaction.source.public_key + "." + "%d" % (te.transaction.sequence - 1)
                    tx_times[tx_id] = close_time

                response = requests.get(transactions["_links"]["next"]["href"])
                transactions = response.json()

        with open("tx_finalized_times.txt", "w") as tx_finalized_times_file:
            for tx_id, close_time in tx_times.items():
                tx_finalized_times_file.write("%s,%d\n" % (tx_id, close_time))

    @experiment_callback
    def stop(self):
        self._logger.info("Stopping Stellar...")
        if self.postgres_process:
            self._logger.info("Killing postgres")
            os.system("pkill -f postgres")
        if self.validator_process:
            self._logger.info("Killing validator")
            self.validator_process.terminate()
        if self.horizon_process:
            self._logger.info("Killing horizon")
            self.horizon_process.terminate()

        loop = get_event_loop()
        loop.stop()
