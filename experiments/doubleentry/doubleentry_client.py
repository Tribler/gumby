#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.dispersy.candidate import Candidate


class DoubleEntryClient(DispersyExperimentScriptClient):

    _SECURITY_LEVEL = u'high'

    def __init__(self, *argv, **kwargs):
        from Tribler.community.doubleentry.community import DoubleEntryCommunity

        msg("Starting DoubleEntry client")
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = DoubleEntryCommunity

    def registerCallbacks(self):
        self.scenario_runner.register(self.request_signature, 'request_signature')
        self.scenario_runner.register(self.draw_graph, 'draw_graph')
        self.scenario_runner.register(self.close, 'close')

    def online(self):
        msg("DEC going online!")
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
            self._community.publish_signature_request_message(candidate)

    def draw_graph(self):
        from Tribler.community.doubleentry.experiments import GraphDrawer

        msg("Drawing graph")
        graph_drawer = GraphDrawer(self.community.persistence)
        graph_drawer.draw_graph()

    def close(self):
        msg("close command received")
        self._community.unload_community()

if __name__ == '__main__':
    DoubleEntryClient.scenario_file = environ.get('SCENARIO_FILE', 'doubleentry.scenario')
    main(DoubleEntryClient)