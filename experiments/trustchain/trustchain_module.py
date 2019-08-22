import json
import os
from random import randint, random, choice
import csv
from time import time

from binascii import hexlify
from twisted.internet.task import LoopingCall

from ipv8.attestation.trustchain.community import TrustChainCommunity
from ipv8.attestation.trustchain.listener import BlockListener

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule


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
        return True

    def received_block(self, block):
        # Add block to stat file
        if not self.start_time:
            # First block received
            self.start_time = time()
        with open(self.file_name, "a") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', "seq_num", "link"])
            writer.writerow({"time": time() - self.start_time, 'transaction': str(block.transaction),
                             'seq_num': block.sequence_number, "link": block.link_sequence_number
                             })


@static_module
class TrustchainModule(IPv8OverlayExperimentModule):
    def __init__(self, experiment):
        super(TrustchainModule, self).__init__(experiment, TrustChainCommunity)
        self.request_signatures_lc = None
        self.num_blocks_in_db_lc = None
        self.block_stat_file = None
        self.request_ds_lc = None

    def on_ipv8_available(self, _):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    def get_peer_public_key(self, peer_id):
        # override the default implementation since we use the trustchain key here.
        return self.all_vars[peer_id]['trustchain_public_key']

    @experiment_callback
    def turn_off_broadcast(self):
        self.overlay.settings.broadcast_blocks = False

    @experiment_callback
    def hide_blocks(self):
        self.overlay.settings.self.is_hiding = True

    @experiment_callback
    def set_ttl(self, value):
        self.overlay.settings.ttl = int(value)
        self._logger.info("Setting ttl for broadcast to %s", value)

    @experiment_callback
    def set_fanout(self, value):
        self.overlay.settings.broadcast_fanout = int(value)
        self._logger.info("Setting broadcast to %s", value)


    @experiment_callback
    def turn_informed_broadcast(self):
        self.overlay.settings.use_informed_broadcast = True
        if os.getenv('IB_TTL'):
            self.set_ttl(os.getenv('IB_TTL'))
        if os.getenv('IB_FANOUT'):
            self.set_fanout(os.getenv('IB_FANOUT'))

    @experiment_callback
    def init_leader_trustchain(self):
        # Open projects output directory and save blocks arrival time
        self.block_stat_file = os.path.join(os.environ['PROJECT_DIR'], 'output', 'leader_blocks_time_'
                                            + str(self.my_id) + '.csv')
        with open(self.block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', "seq_num", "link"])
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
        self.tribler_config.set_trustchain_memory_db(True)

    @experiment_callback
    def set_validation_range(self, value):

        if os.getenv('VALID_WINDOW'):
            value = int(os.getenv('VALID_WINDOW'))

        self._logger.info("Setting validation range to %s", value)

        self.overlay.settings.validation_range = int(value)

    @experiment_callback
    def enable_crawler(self):
        self.overlay.settings.crawler = True

    @experiment_callback
    def start_requesting_signatures(self):
        self.request_signatures_lc = LoopingCall(self.request_random_signature)
        self.request_signatures_lc.start(1)

    @experiment_callback
    def stop_requesting_signatures(self):
        self.request_signatures_lc.stop()

    @experiment_callback
    def start_req_sign_with_random_double_spends(self, batch=1, chance=0.1):

        if os.getenv('DS_BATCH'):
            batch = int(os.getenv('DS_BATCH'))
        if os.getenv('DS_CHANCE'):
            chance = float(os.getenv('DS_CHANCE'))

        self.request_ds_lc = LoopingCall(self.make_double_spend, batch, chance)
        self.request_ds_lc.start(1)

    @experiment_callback
    def stop_req_sign_with_random_double_spends(self):
        self.request_ds_lc.stop()

    @experiment_callback
    def start_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_lc = LoopingCall(self.check_num_blocks_in_db)
        self.num_blocks_in_db_lc.start(1)

    @experiment_callback
    def stop_monitor_num_blocks_in_db(self):
        self.num_blocks_in_db_lc.stop()

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
    def request_random_signature(self, attach_to_block=None):
        """
        Request a random signature from one of your known verified peers
        """
        rand_up = randint(1, 1000)
        rand_down = randint(1, 1000)

        if not self.overlay.network.verified_peers:
            self._logger.warning("No verified peers to request random signature from!")
            return

        self.request_signature_from_peer(choice(list(self.overlay.get_peers())),
                                         rand_up * 1024 * 1024, rand_down * 1024 * 1024,
                                         attached_block=attach_to_block)

    @experiment_callback
    def make_double_spend(self, num_ds=1, chance=0.3):
        blk = self.overlay.persistence.get_latest(self.overlay.my_peer.public_key.key_to_bin())
        if not blk:
            self._logger.error("Cannot find last block of own peer")
            self.request_random_signature()
        else:
            if random < chance:
                for _ in range(num_ds):
                    self.request_random_signature(blk.sequence_number - 1)
            else:
                self.request_random_signature()

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

        self.request_signatures_lc = LoopingCall(self.send_to_leader_peer, int(block_num))
        self.request_signatures_lc.start(1)

    def request_signature_from_peer(self, peer, up, down, attached_block=None):
        peer_id = self.experiment.get_peer_id(peer.address[0], peer.address[1])
        self._logger.info("%s: Requesting signature from peer: %s", self.my_id, peer_id)
        transaction = {"up": up, "down": down, "from_peer": self.my_id, "to_peer": peer_id}
        self.overlay.sign_block(peer, peer.public_key.key_to_bin(),
                                block_type=b'test', transaction=transaction,
                                double_spend_block=attached_block)

    def check_num_blocks_in_db(self):
        """
        Check the total number of blocks we have in the database and write it to a file.
        """
        num_blocks = len(self.overlay.persistence.get_all_blocks())
        with open('num_trustchain_blocks.txt', 'a') as output_file:
            elapsed_time = time.time() - self.experiment.scenario_runner.exp_start_time
            output_file.write("%f,%d\n" % (elapsed_time, num_blocks))

    @experiment_callback
    def commit_blocks_to_db(self):
        if self.session.config.use_trustchain_memory_db():
            self.overlay.persistence.commit(self.overlay.my_peer.public_key.key_to_bin())

    @experiment_callback
    def write_trustchain_statistics(self):
        from anydex.wallet.tc_wallet import TrustchainWallet
        with open('trustchain.txt', 'w') as trustchain_file:
            wallet = TrustchainWallet(self.overlay)
            trustchain_file.write(json.dumps(wallet.get_statistics()))
