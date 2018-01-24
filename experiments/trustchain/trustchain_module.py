from random import randint, choice

from Tribler.Core import permid

from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule

from twisted.internet.task import LoopingCall

from Tribler.community.trustchain.community import TrustChainCommunity


@static_module
class TrustchainModule(CommunityExperimentModule):
    def __init__(self, experiment):
        super(TrustchainModule, self).__init__(experiment, TrustChainCommunity)
        self.request_signatures_lc = LoopingCall(self.request_random_signature)

    def on_id_received(self):
        super(TrustchainModule, self).on_id_received()

        # We need the trustchain key at this point. However, the configured session is not started yet. So we generate
        # the keys here and place them in the correct place. When the session starts it will load these keys.
        trustchain_keypair = permid.generate_keypair_trustchain()
        trustchain_pairfilename = self.tribler_config.get_trustchain_permid_keypair_filename()
        permid.save_keypair_trustchain(trustchain_keypair, trustchain_pairfilename)
        permid.save_pub_key_trustchain(trustchain_keypair, "%s.pub" % trustchain_pairfilename)

        self.vars['trustchain_public_key'] = trustchain_keypair.pub().key_to_bin().encode("base64")

    def get_candidate_public_key(self, candidate_id):
        # override the default implementation since we use the trustchain key here.
        return self.all_vars[candidate_id]['trustchain_public_key']

    def on_dispersy_available(self, dispersy):
        self.introduce_peers()

    @experiment_callback
    def start_requesting_signatures(self):
        self.request_signatures_lc.start(1)

    @experiment_callback
    def stop_requesting_signatures(self):
        self.request_signatures_lc.stop()

    @experiment_callback
    def request_signature(self, candidate_id, up, down):
        self.request_signature_from_candidate(self.get_candidate(candidate_id), up, down)

    @experiment_callback
    def request_crawl(self, candidate_id, sequence_number):
        self._logger.info("%s: Requesting block: %s For candidate: %s" % (self.my_id, sequence_number, candidate_id))
        self.community.send_crawl_request(self.get_candidate(candidate_id),
                                          self.get_candidate(candidate_id).get_member().public_key,
                                          int(sequence_number))

    @experiment_callback
    def request_random_signature(self):
        """
        Request a random signature from one of your known candidates
        """
        rand_up = randint(1, 1000)
        rand_down = randint(1, 1000)

        known_candidates = list(self.community.dispersy_yield_verified_candidates())
        self.request_signature_from_candidate(choice(known_candidates), rand_up * 1024 * 1024, rand_down * 1024 * 1024)

    def request_signature_from_candidate(self, candidate, up, down):
        self._logger.info("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate))
        transaction = {"up": up, "down": down}
        self.community.sign_block(candidate, candidate.get_member().public_key, transaction)
