import csv
import json
import os
from random import choice, randint
from time import time

from anydex.trustchain.community import TrustChainCommunity
from anydex.trustchain.listener import BlockListener

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.util import run_task


class FakeBlockListener(BlockListener):
    """
    Block listener that only signs blocks
    """

    def should_sign(self, _):
        return True

    def received_block(self, block):
        pass


class GeneratedBlockListener(BlockListener):
    """
    This block listener to measure throughput.
    This peer will not sign blocks
    """

    def __init__(self, mes_file):
        # File to safe measurements
        self.file_name = mes_file
        self.start_time = None

    def should_sign(self, _):
        return False

    def received_block(self, block):
        # Add block to stat file
        if not self.start_time:
            # First block received
            self.start_time = time()
        with open(self.file_name, "a") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction'])
            writer.writerow({"time": time() - self.start_time, 'transaction': str(block.transaction)})


class TrustchainModule(IPv8OverlayExperimentModule):
    def __init__(self, experiment):
        super(TrustchainModule, self).__init__(experiment, TrustChainCommunity)
        self.request_signatures_lc = None
        self.num_blocks_in_db_task = None
        self.block_stat_file = None
        self.request_signatures_task = None

    def get_peer_public_key(self, peer_id):
        # override the default implementation since we use the trustchain key here.
        return self.all_vars[peer_id]['trustchain_public_key']

    @experiment_callback
    def turn_off_broadcast(self):
        self.overlay.settings.broadcast_blocks = False

    @experiment_callback
    def init_leader_trustchain(self):
        # Open projects output directory and save blocks arrival time
        self.block_stat_file = os.path.join(os.environ['PROJECT_DIR'], 'output', 'leader_blocks_time.csv')
        with open(self.block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction'])
            writer.writeheader()
        self.overlay.add_listener(GeneratedBlockListener(self.block_stat_file), [b'test'])

    @experiment_callback
    def init_trustchain(self):
        self.overlay.add_listener(FakeBlockListener(), [b'test'])

    @experiment_callback
    def disable_max_peers(self):
        self.overlay.max_peers = -1

    @experiment_callback
    def enable_trustchain_memory_db(self):
        self.tribler_config.trustchain.memory_db = True

    @experiment_callback
    def set_validation_range(self, value):
        self.overlay.settings.validation_range = int(value)

    @experiment_callback
    def enable_crawler(self):
        self.overlay.settings.crawler = True

    @experiment_callback
    def start_requesting_signatures(self):
        self.request_signatures_task = run_task(self.request_random_signature, interval=1)

    @experiment_callback
    def stop_requesting_signatures(self):
        self.request_signatures_task.cancel()

    @experiment_callback
    def start_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_task = run_task(self.check_num_blocks_in_db, interval=1)

    @experiment_callback
    def stop_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_task.cancel()

    @experiment_callback
    def request_signature(self, peer_id, up, down):
        self.request_signature_from_peer(self.get_peer(peer_id), up, down)

    @experiment_callback
    def request_crawl(self, peer_id, sequence_number):
        self._logger.info("%s: Requesting block: %s for peer: %s" % (self.my_id, sequence_number, peer_id))
        self.overlay.send_crawl_request(self.get_peer(peer_id),
                                        self.get_peer(peer_id).public_key.key_to_bin(),
                                        int(sequence_number))

    @experiment_callback
    def request_random_signature(self):
        """
        Request a random signature from one of your known verified peers
        """
        rand_up = randint(1, 1000)
        rand_down = randint(1, 1000)

        if not self.overlay.network.verified_peers:
            self._logger.warning("No verified peers to request random signature from!")
            return

        verified_peers = list(self.overlay.network.verified_peers)
        self.request_signature_from_peer(choice(verified_peers), rand_up * 1024 * 1024, rand_down * 1024 * 1024)

    def send_to_leader_peer(self, block_num):
        leader_peer = self.overlay.network.verified_peers[0]
        for _ in range(block_num):
            rand_up = randint(1, 1000)
            rand_down = randint(1, 1000)
            self.request_signature_from_peer(leader_peer, rand_up, rand_down)

    @experiment_callback
    def start_spamming_leader_peer(self, block_num=100):
        """
        Send block_num of blocks per second to leader peer per second.
        NUM_TX environment variable will be used instead of block_num if defined
        :param block_num: number of blocks per sec to send to leader peer
        """
        if os.getenv('NUM_TX'):
            block_num = int(os.getenv('NUM_TX'))

        self.request_signatures_task = run_task(self.send_to_leader_peer, int(block_num), interval=1)

    def request_signature_from_peer(self, peer, up, down):
        peer_id = self.experiment.get_peer_id(peer.address[0], peer.address[1])
        self._logger.info("%s: Requesting signature from peer: %s", self.my_id, peer_id)
        transaction = {"up": up, "down": down, "from_peer": self.my_id, "to_peer": peer_id}
        self.overlay.sign_block(peer, peer.public_key.key_to_bin(), block_type=b'test', transaction=transaction)

    def check_num_blocks_in_db(self):
        """
        Check the total number of blocks we have in the database and write it to a file.
        """
        num_blocks = len(self.overlay.persistence.get_all_blocks())
        with open('num_trustchain_blocks.txt', 'a') as output_file:
            elapsed_time = time() - self.experiment.scenario_runner.exp_start_time
            output_file.write("%f,%d\n" % (elapsed_time, num_blocks))

    @experiment_callback
    def commit_blocks_to_db(self):
        if self.gumby_session.config.trustchain.memory_db:
            self.overlay.persistence.commit(self.overlay.my_peer.public_key.key_to_bin())

    @experiment_callback
    def write_trustchain_statistics(self):
        from anydex.wallet.tc_wallet import TrustchainWallet
        with open('trustchain.txt', 'w') as trustchain_file:
            wallet = TrustchainWallet(self.overlay)
            trustchain_file.write(json.dumps(wallet.get_statistics()))
