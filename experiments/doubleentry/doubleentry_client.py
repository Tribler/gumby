#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath
from time import sleep
from hashlib import sha1
import base64

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.dispersy.candidate import Candidate
from Tribler.dispersy.member import Member
from Tribler.community.doubleentry.community import DoubleEntryCommunity


class DoubleEntryClient(DispersyExperimentScriptClient):

    _SECURITY_LEVEL = u'high'

    def __init__(self, *argv, **kwargs):
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        msg("Starting DoubleEntry client")
        # Set the default DoubleEntryCommunity as community
        self.community_class = DoubleEntryCommunity
        self.vars['public_key'] = base64.encodestring(self.my_member_key)

    def registerCallbacks(self):
        self.scenario_runner.register(self.introduce_candidates, 'introduce_candidates')
        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.close, 'close')

    def set_community_class(self, community_type='DoubleEntryCommunity'):
        """
        Sets the community class of this gumby node to a special community.
        """
        msg("CommunityType: %s" % community_type)
        if community_type == 'DoubleEntryDelayCommunity':
            msg("Starting DoubleEntry client with: " + DoubleEntryDelayCommunity.__name__)
            self.community_class = DoubleEntryDelayCommunity
        elif community_type == 'DoubleEntryNoResponseCommunity':
            msg("Starting DoubleEntry client with: " + DoubleEntryNoResponseCommunity.__name__)
            self.community_class = DoubleEntryNoResponseCommunity
        else:
            raise RuntimeError("Tried to set to unknown community.")

    def online(self):
        DispersyExperimentScriptClient.online(self)

    def request_signature(self, candidate_id=0):
        msg("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate_id))
        if candidate_id == 0:
            for c in self.all_vars.itervalues():
                candidate = Candidate((str(c['host']), c['port']), False)
                self._community.publish_signature_request_message(candidate)
        else:
            target = self.all_vars[candidate_id]
            candidate = self._community.get_candidate((str(target['host']), target['port']))
            print("Member %s" % candidate.get_member())
            print("Type %s" % type(candidate.get_member()))
            self._community.publish_signature_request_message(candidate)

    def introduce_candidates(self):
        """
        Introduce every candidate to each other so that later the candidates can be retrieved and used as a destination.
        """
        msg("Introducing every candidate")
        for node in self.all_vars.itervalues():
            candidate = Candidate((str(node['host']), node['port']), False)
            self._community.add_discovered_candidate(candidate)

    def close(self):
        msg("close command received")
        self._community.unload_community()


class DoubleEntryDelayCommunity(DoubleEntryCommunity):
    """
    Test Community that does not respond to signature requests.
    """
    delay = 2

    def __init__(self, *args, **kwargs):
        super(DoubleEntryDelayCommunity, self).__init__(*args, **kwargs)

    def on_signature_request(self, messages):
        """
        Ignore the signature requests.
        :param messages: the to be ignored requests
        """
        self._logger.info("Received %s message(s) that will delayed for %s." % (len(messages), self.delay))
        sleep(self.delay)
        self._logger.info("Delay over.")
        super(DoubleEntryDelayCommunity, self).on_signature_request(messages)


class DoubleEntryNoResponseCommunity(DoubleEntryCommunity):
    """
    Test Community that does not respond to signature requests.
    """

    def __init__(self, *args, **kwargs):
        super(DoubleEntryNoResponseCommunity, self).__init__(*args, **kwargs)

    def on_signature_request(self, messages):
        """
        Ignore the signature requests.
        :param messages: the to be ignored requests
        """
        self._logger.info("Received " + str(len(messages)) + " message(s) that will be ignored.")
        return


class TestMember(Member):
    """
    TestMember that is only used to add a Member with a public key to a candidate.
    """

    def __init__(self, public_key):
        self._public_key = public_key
        self._mid = sha1(public_key).digest()
        # No db id known.
        self._database_id = -1
        # Test length determined and might become incorrect in the future.
        self._signature_length = 40
        # A Candidate does not have a private key, because it is a different node.
        self._private_key = None

    def __str__(self):
        return str(self._public_key)

if __name__ == '__main__':
    DoubleEntryClient.scenario_file = environ.get('SCENARIO_FILE', 'doubleentry.scenario')
    main(DoubleEntryClient)