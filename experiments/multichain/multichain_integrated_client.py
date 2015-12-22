#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath
import base64

from gumby.experiments.dispersyclient import main
from experiments.multichain.multichain_client import MultiChainDelayCommunity, MultiChainNoResponseCommunity
from experiments.dispersy.hiddenservices_client import HiddenServicesClient

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.dispersy.candidate import Candidate
from Tribler.community.multichain.community import MultiChainCommunity, MultiChainCommunityCrawler, MultiChainScheduler


class MultiChainIntegratedClient(HiddenServicesClient):
    """
    Gumby client to start the MultiChain Community in conjunction with the HiddenServicesClient.
    """

    def __init__(self, *args, **kwargs):
        HiddenServicesClient.__init__(self, *args, **kwargs)
        msg("Starting MultiChain client")
        """ Set the default MultiChainCommunity as community """
        self._multichain_type = MultiChainCommunity
        """ MultiChain is initialized later."""
        self._multichain = None
        self.vars['public_key'] = base64.encodestring(self.my_member_key)
        """ Override the test files to speed up the test."""
        # 10 Mb
        self.test_file_size = 100 * 1024 * 1024
        self.min_circuits = 1
        self.max_circuits = 1

    def registerCallbacks(self):
        HiddenServicesClient.registerCallbacks(self)
        self.scenario_runner.register(self.set_multichain_type, 'set_multichain_type')
        self.scenario_runner.register(self.introduce_candidates, 'introduce_candidates')
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.request_crawl, 'request_crawl')
        self.scenario_runner.register(self.close, 'close')
        """ Integrated callbacks"""
        self.scenario_runner.register(self.start_multichain, 'start_multichain')
        self.scenario_runner.register(self.start_scheduler, 'start_scheduler')

    def set_multichain_type(self, multichain_type='MultiChainCommunity'):
        """
        Sets the community class of this gumby node to a special community.
        """
        msg("CommunityType: %s" % multichain_type)
        if multichain_type == 'MultiChainDelayCommunity':
            msg("Starting MultiChain client with: " + MultiChainDelayCommunity.__name__)
            self._multichain_type = MultiChainDelayCommunity
        elif multichain_type == 'MultiChainNoResponseCommunity':
            msg("Starting MultiChain client with: " + MultiChainNoResponseCommunity.__name__)
            self._multichain_type = MultiChainNoResponseCommunity
        elif multichain_type == 'MultiChainCommunityCrawler':
            msg("Starting MultiChain client with: " + MultiChainCommunityCrawler.__name__)
            self._multichain_type = MultiChainCommunityCrawler
        else:
            raise RuntimeError("Tried to set to unknown community.")

    def start_multichain(self):
        """
        Load the multichain community into Dispersy.
        :return: None
        """
        communities = self._dispersy.define_auto_load(self._multichain_type, self._my_member, (), load=True)
        """ The MultiChain community has to be saved to be used by gumby. """
        for community in communities:
            if isinstance(community, MultiChainCommunity):
                self._multichain = community
                self._logger.info("MultiChain community loaded.")
                break
        # Same as the standalone client, the multichain community needs to keep it's candidates around. The original is
        # used here instead of a derived class. So to 'override' the candidate cleanup, monkeypatch the original object
        # with a bound instance function, obtained through the __get__ descriptor of the function object.
        def cleanup_candidates(self):
            return 0
        self._multichain.cleanup_candidates = cleanup_candidates.__get__(self._multichain, self._multichain_type)

    def start_scheduler(self):
        """ Wire the MultiChainScheduler into the Tunnel Community. """
        scheduler = MultiChainScheduler(self._multichain)
        self._community.multichain_scheduler = scheduler
        self._logger.info("MultiChainScheduler loaded.")

    def request_signature(self, candidate_id):
        msg("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate_id))
        target = self.all_vars[candidate_id]
        candidate = self._multichain.get_candidate((str(target['host']), target['port']))
        self._multichain.publish_signature_request_message(candidate, 1, 1)

    def request_crawl(self, candidate_id, sequence_number):
        msg("%s: Requesting block: %s For candidate: %s" % (self.my_id, sequence_number, candidate_id))
        target = self.all_vars[candidate_id]
        candidate = self._multichain.get_candidate((str(target['host']), target['port']))
        self._multichain.send_crawl_request(candidate, int(sequence_number))

    def introduce_candidates(self):
        """
        Introduce every candidate to each other so that later the candidates can be retrieved and used as a destination.
        """
        HiddenServicesClient.introduce_candidates(self)
        msg("Introducing every candidate")
        for node in self.all_vars.itervalues():
            candidate = Candidate((str(node['host']), node['port']), False)
            self._multichain.add_discovered_candidate(candidate)
            candidate = self._multichain.get_candidate((str(node['host']), node['port']))
            member = self._multichain.get_member(public_key=base64.decodestring(str(node['public_key'])))
            member.add_identity(self._multichain)
            candidate.associate(member)

    def close(self):
        msg("close command received")
        self._community.unload_community()
        self._multichain.unload_community()

if __name__ == '__main__':
    MultiChainIntegratedClient.scenario_file = environ.get('SCENARIO_FILE', 'multichain_integrated.scenario')
    main(MultiChainIntegratedClient)
