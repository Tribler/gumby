#!/usr/bin/env python2
import base64
import os
from random import randint, choice

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from gumby.experiments.dispersyclient import main
from gumby.experiments.triblerclient import TriblerExperimentScriptClient

from Tribler.community.multichain.community import MultiChainCommunity
from Tribler.dispersy.candidate import Candidate


class MultiChainClient(TriblerExperimentScriptClient):
    """
    This client is responsible for managing experiments with the MultiChain community.
    """
    def __init__(self, params):
        super(MultiChainClient, self).__init__(params)
        self.multichain_community = None
        self.vars['public_key'] = base64.encodestring(self.my_member_key)
        self.request_signatures_lc = LoopingCall(self.request_random_signature)

    def setup_session_config(self):
        config = super(MultiChainClient, self).setup_session_config()
        config.set_tunnel_community_enabled(True)
        config.set_enable_multichain(False)  # We're loading our own multichain community
        return config

    def registerCallbacks(self):
        super(MultiChainClient, self).registerCallbacks()
        self.scenario_runner.register(self.request_signature)
        self.scenario_runner.register(self.request_crawl)
        self.scenario_runner.register(self.start_requesting_signatures)
        self.scenario_runner.register(self.stop_requesting_signatures)
        self.scenario_runner.register(self.load_multichain_community)

    def request_signature(self, candidate_id, up, down):
        target = self.all_vars[candidate_id]
        self._logger.info("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate_id))
        candidate = Candidate((str(target['host']), 21000 + int(candidate_id)), False)
        if not candidate.get_member():
            member = self.multichain_community.get_member(public_key=base64.decodestring(str(target['public_key'])))
            member.add_identity(self.multichain_community)
            candidate.associate(member)

        self.request_signature_from_candidate(candidate, up, down)

    def request_signature_from_candidate(self, candidate, up, down):
        self.multichain_community.schedule_block(candidate, int(up), int(down))

    def request_crawl(self, candidate_id, sequence_number):
        target = self.all_vars[candidate_id]
        self._logger.info("%s: Requesting block: %s For candidate: %s" % (self.my_id, sequence_number, candidate_id))
        candidate = self.multichain_community.get_candidate((str(target['host']), target['port']))
        self.multichain_community.send_crawl_request(candidate, int(sequence_number))

    def start_requesting_signatures(self):
        self.request_signatures_lc.start(1)

    def stop_requesting_signatures(self):
        self.request_signatures_lc.stop()

    def request_random_signature(self):
        """
        Request a random signature from one of your known candidates
        """
        rand_up = randint(1, 1000)
        rand_down = randint(1, 1000)
        known_candidates = list(self.multichain_community.dispersy_yield_verified_candidates())
        self.request_signature_from_candidate(choice(known_candidates), rand_up * 1024 * 1024, rand_down * 1024 * 1024)

    def load_multichain_community(self):
        """
        Load the multichain community
        """
        keypair = self.session.multichain_keypair
        my_member = self.session.get_dispersy_instance().get_member(private_key=keypair.key_to_bin())
        self.multichain_community = self.session.get_dispersy_instance().define_auto_load(
            MultiChainCommunity, my_member, load=True, kargs={'tribler_session': self.session})[0]

        # The multichain community needs to keep it's candidates around. So to 'override' the candidate cleanup, we
        # monkeypatch the original object. Using the above method bound to the community instance.
        self.multichain_community.cleanup_candidates = lambda: 0

if __name__ == '__main__':
    MultiChainClient.scenario_file = os.environ.get('SCENARIO_FILE', 'multichain_1000.scenario')
    main(MultiChainClient)
