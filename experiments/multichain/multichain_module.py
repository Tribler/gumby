from sys import maxint
from time import time

from random import randint, choice

from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule

from twisted.internet.task import LoopingCall

from Tribler.Core import permid
from Tribler.community.multichain.community import MultiChainCommunity, PendingBytes


@static_module
class MultichainModule(CommunityExperimentModule):
    def __init__(self, experiment):
        super(MultichainModule, self).__init__(experiment, MultiChainCommunity)
        self.request_signatures_lc = LoopingCall(self.request_random_signature)

    def on_id_received(self):
        super(MultichainModule, self).on_id_received()
        self.session_config.set_enable_multichain(True)

        # We need the multichain key at this point. However, the configured session is not started yet. So we generate
        # the keys here and place them in the correct place. When the session starts it will load these keys.
        multichain_keypair = permid.generate_keypair_multichain()
        multichain_pairfilename = self.session_config.get_multichain_permid_keypair_filename()
        permid.save_keypair_multichain(multichain_keypair, multichain_pairfilename)
        permid.save_pub_key_multichain(multichain_keypair, "%s.pub" % multichain_pairfilename)

        self.vars['multichain_public_key'] = multichain_keypair.pub().key_to_bin().encode("base64")

    def get_candidate_public_key(self, candidate_id):
        # override the default implementation since we use the multichain key here.
        return self.all_vars[candidate_id]['multichain_public_key']

    def on_dispersy_available(self, dispersy):
        self.introduce_peers()

    @experiment_callback
    def set_unlimited_pending(self):
        # each peer has an almost unlimited number of bytes pending at each other peer. So we can sign stuff.
        for candidate_id in self.all_vars.iterkeys():
            if int(candidate_id) != self.my_id:
                pk = self.get_candidate(candidate_id).get_member().public_key
                self.community.pending_bytes[pk] = PendingBytes(maxint/2, maxint/2)

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
        self._logger.error("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate))
        self.community.sign_block(candidate, candidate.get_member().public_key, int(up), int(down))
