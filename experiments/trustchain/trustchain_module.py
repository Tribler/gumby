import json
import time
from random import randint, choice

from Tribler.Core import permid
from Tribler.Core.Modules.wallet.tc_wallet import TrustchainWallet
from Tribler.pyipv8.ipv8.attestation.trustchain.community import TrustChainCommunity
from Tribler.pyipv8.ipv8.attestation.trustchain.listener import BlockListener

from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule

from twisted.internet.task import LoopingCall


@static_module
class TrustchainModule(IPv8OverlayExperimentModule, BlockListener):
    def __init__(self, experiment):
        super(TrustchainModule, self).__init__(experiment, TrustChainCommunity)
        self.request_signatures_lc = None
        self.num_blocks_in_db_lc = None

    def on_id_received(self):
        super(TrustchainModule, self).on_id_received()

        # We need the trustchain key at this point. However, the configured session is not started yet. So we generate
        # the keys here and place them in the correct place. When the session starts it will load these keys.
        trustchain_keypair = permid.generate_keypair_trustchain()
        trustchain_pairfilename = self.tribler_config.get_trustchain_keypair_filename()
        permid.save_keypair_trustchain(trustchain_keypair, trustchain_pairfilename)
        permid.save_pub_key_trustchain(trustchain_keypair, "%s.pub" % trustchain_pairfilename)

        self.vars['trustchain_public_key'] = trustchain_keypair.pub().key_to_bin().encode("base64")

    def on_dispersy_available(self, dispersy):
        # Disable threadpool messages
        self.overlay._use_main_thread = True

    def get_peer_public_key(self, peer_id):
        # override the default implementation since we use the trustchain key here.
        return self.all_vars[peer_id]['trustchain_public_key']

    @experiment_callback
    def init_trustchain(self):
        self.overlay.add_listener(self, ['test'])

    @experiment_callback
    def enable_trustchain_memory_db(self):
        self.tribler_config.set_trustchain_memory_db(True)

    @experiment_callback
    def start_requesting_signatures(self):
        self.request_signatures_lc = LoopingCall(self.request_random_signature)
        self.request_signatures_lc.start(1)

    @experiment_callback
    def stop_requesting_signatures(self):
        self.request_signatures_lc.stop()

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

    def request_signature_from_peer(self, peer, up, down):
        self._logger.info("%s: Requesting signature from peer: %s" % (self.my_id, peer))
        transaction = {"up": up, "down": down}
        self.overlay.sign_block(peer, peer.public_key.key_to_bin(), block_type='test', transaction=transaction)

    def check_num_blocks_in_db(self):
        """
        Check the total number of blocks we have in the database and write it to a file.
        """
        num_blocks = len(self.overlay.persistence.get_all_blocks())
        with open('num_trustchain_blocks.txt', 'a') as output_file:
            elapsed_time = time.time() - self.experiment.scenario_runner.exp_start_time
            output_file.write("%f,%d\n" % (elapsed_time, num_blocks))

    def should_sign(self, block):
        return True

    def received_block(self, block):
        pass

    @experiment_callback
    def commit_blocks_to_db(self):
        if self.session.config.use_trustchain_memory_db():
            self.overlay.persistence.commit(self.overlay.my_peer.public_key.key_to_bin())

    @experiment_callback
    def write_trustchain_statistics(self):
        with open('trustchain.txt', 'w', 0) as trustchain_file:
            wallet = TrustchainWallet(self.overlay)
            trustchain_file.write(json.dumps(wallet.get_statistics()))
