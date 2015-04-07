#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


class DoubleEntryClient(DispersyExperimentScriptClient):

    _SECURITY_LEVEL = u'high'

    def __init__(self, *argv, **kwargs):
        print "DEC started"
        from Tribler.community.doubleentry.community import DoubleEntryCommunity

        msg("Starting DoubleEntry client")
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = DoubleEntryCommunity

        # self.set_community_kwarg('integrate_with_tribler', False)

    def registerCallbacks(self):
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.draw_graph, 'draw_graph')

    def online(self):
        print "DEC going online!"
        DispersyExperimentScriptClient.online(self)

    def request_signature(self):
        print "Requesting Signature"
        self._community.publish_signature_request_message()

    def draw_graph(self):
        from Tribler.community.doubleentry.experiments import GraphDrawer

        print "Drawing graph"
        graph_drawer = GraphDrawer(self.community.persistence)
        graph_drawer.draw_graph()

if __name__ == '__main__':
    DoubleEntryClient.scenario_file = environ.get('SCENARIO_FILE', 'doubleentry.scenario')
    main(DoubleEntryClient)