#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath
from time import sleep
import base64

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.dispersy.candidate import Candidate
from Tribler.community.multichain.community import MultiChainCommunity, MultiChainCommunityCrawler


class MultiChainClient(DispersyExperimentScriptClient):
    """
    Gumby client to start the MultiChain Community
    """

    def __init__(self, *argv, **kwargs):
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        msg("Starting MultiChain client")
        # Set the default MultiChainCommunity as community
        self.community_class = MultiChainCommunity
        self.vars['public_key'] = base64.encodestring(self.my_member_key)

    def registerCallbacks(self):
        self.scenario_runner.register(self.introduce_candidates, 'introduce_candidates')
        self.scenario_runner.register(self.set_multichain_type, 'set_multichain_type')
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.request_block, 'request_block')
        self.scenario_runner.register(self.close, 'close')

    def set_multichain_type(self, multichain_type='MultiChainCommunity'):
        """
        Sets the community class of this gumby node to a special community.
        """
        msg("CommunityType: %s" % multichain_type)
        if multichain_type == 'MultiChainDelayCommunity':
            msg("Starting MultiChain client with: " + MultiChainDelayCommunity.__name__)
            self.community_class = MultiChainDelayCommunity
        elif multichain_type == 'MultiChainNoResponseCommunity':
            msg("Starting MultiChain client with: " + MultiChainNoResponseCommunity.__name__)
            self.community_class = MultiChainNoResponseCommunity
        elif multichain_type == 'MultiChainCommunityCrawler':
            msg("Starting MultiChain client with: " + MultiChainCommunityCrawler.__name__)
            self.community_class = MultiChainCommunityCrawler
        else:
            raise RuntimeError("Tried to set to unknown community:%s." % multichain_type)

    def online(self):
       DispersyExperimentScriptClient.online(self)

    def request_signature(self, candidate_id):
        msg("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate_id))
        target = self.all_vars[candidate_id]
        candidate = self._community.get_candidate((str(target['host']), target['port']))
        print("Candidate known:%s" % candidate.get_member())
        self._community.publish_signature_request_message(candidate, 1, 1)

    def request_block(self, candidate_id, sequence_number):
        msg("%s: Requesting block: %s For candidate: %s" % (self.my_id, sequence_number, candidate_id))
        target = self.all_vars[candidate_id]
        candidate = self._community.get_candidate((str(target['host']), target['port']))
        print("Candidate: %s" % candidate.get_member())
        self._community.publish_request_block_message(candidate, int(sequence_number))

    def introduce_candidates(self):
        """
        Introduce every candidate to each other so that later the candidates can be retrieved and used as a destination.
        """
        msg("Introducing every candidate")
        for node in self.all_vars.itervalues():
            candidate = Candidate((str(node['host']), node['port']), False)
            self._community.add_discovered_candidate(candidate)

    @property
    def my_member_key_curve(self):
        return u"curve25519"

    def close(self):
        msg("close command received")
        self._community.unload_community()


class MultiChainDelayCommunity(MultiChainCommunity):
    """
    Test Community that delays signature requests.
    """
    delay = 3

    def __init__(self, *args, **kwargs):
        super(MultiChainDelayCommunity, self).__init__(*args, **kwargs)

    def allow_signature_request(self, message):
        """
        Ignore the signature requests.
        :param message: the to be delayed request
        """
        self.logger.info("Received signature request that will delayed for %s." % self.delay)
        sleep(self.delay)
        self.logger.info("Delay over.")
        super(MultiChainDelayCommunity, self).allow_signature_request(message)


class MultiChainNoResponseCommunity(MultiChainCommunity):
    """
    Test Community that does not respond to signature requests.
    """

    def __init__(self, *args, **kwargs):
        super(MultiChainNoResponseCommunity, self).__init__(*args, **kwargs)

    def allow_signature_request(self, message):
        """
        Ignore the signature requests.
        :param message: the to be ignored request
        """
        self.logger.info("Received signature request that will be ignored.")
        return

if __name__ == '__main__':
    MultiChainClient.scenario_file = environ.get('SCENARIO_FILE', 'multichain_standalone.scenario')
    main(MultiChainClient)