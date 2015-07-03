#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath
from time import sleep
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
        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.close, 'close')

    def set_community_class(self, community_type='DoubleEntryCommunity'):
        """
        Sets the community class of this gumby node to a special community.
        """
        if community_type == 'DoubleEntryDelayCommunity':
            msg("Starting DoubleEntry client with: " + DoubleEntryDelayCommunity.__name__)
            self.community_class = DoubleEntryDelayCommunity
        elif community_type == 'DoubleEntryNoResponseCommunity':
            msg("Starting DoubleEntry client with: " + DoubleEntryNoResponseCommunity.__name__)
            self.community_class = DoubleEntryNoResponseCommunity

    def online(self):
        msg("Double Entry Client going online!")
        DispersyExperimentScriptClient.online(self)

    def request_signature(self, candidate_id=0):
        msg("%s: Requesting Signature for candidate: %s" % (self.my_id, candidate_id))
        if candidate_id == 0:
            for c in self.all_vars.itervalues():
                candidate = Candidate((str(c['host']), c['port']), False)
                self._community.publish_signature_request_message(candidate)
        else:
            target = self.all_vars[candidate_id]
            candidate = Candidate((str(target['host']), target['port']), False)
            candidate.associate(TestMember(base64.decodestring(target['public_key'])))
            self._community.publish_signature_request_message(candidate)

    def close(self):
        msg("close command received")
        self._community.unload_community()


class DoubleEntryDelayCommunity(DoubleEntryCommunity):
    """
    Test Community that does not respond to signature requests.
    """
    delay = 5

    def __init__(self, *args, **kwargs):
        super(DoubleEntryDelayCommunity, self).__init__(*args, **kwargs)

    def on_signature_request(self, messages):
        """
        Ignore the signature requests.
        :param messages: the to be ignored requests
        """
        self._logger.info("Received %s message(s) that will delayed for %s." % (len(messages), self.delay))
        sleep(5)
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

    def __str__(self):
        return str(self._public_key)


if __name__ == '__main__':
    DoubleEntryClient.scenario_file = environ.get('SCENARIO_FILE', 'doubleentry_timeout.scenario')
    main(DoubleEntryClient)