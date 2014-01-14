import os
import sys
from random import expovariate, random
from gumby.scenario import ScenarioRunner
from collections import defaultdict

class ChurnAnalyzer(ScenarioRunner):

    def __init__(self, filename, outputfile=sys.stdout, max_tstmp=0):
        self._callables = {}
        self._callables['online'] = self.online
        self._callables['offline'] = self.offline
        self._callables['add_friend'] = self.add_friend

        self._peer_state = defaultdict(lambda: "offline")
        self._peer_friends = defaultdict(list)

        sorted_scenario = defaultdict(list)

        prev_tstmp = -1
        for (tstmp, lineno, clb, args, peerspec) in self._parse_scenario(filename):
            if clb in self._callables:
                yes_peers, _ = peerspec

                sorted_scenario[tstmp].append((yes_peers, clb, args))

        tstmps = sorted_scenario.keys()
        tstmps.sort()

        for tstmp in tstmps:
            for yes_peers, clb, args in sorted_scenario[tstmp]:
                for peer in yes_peers:
                        self._callables[clb](peer, *args)

                if prev_tstmp != tstmp:
                    self.print_connections(tstmp, outputfile)
                    prev_tstmp = tstmp

    def _parse_for_this_peer(self, peerspec):
        return True

    def online(self, peer):
        self._peer_state[peer] = "online"

    def offline(self, peer):
        self._peer_state[peer] = "offline"

    def add_friend(self, peer, friend):
        self._peer_friends[peer].append(int(friend))

    def print_connections(self, tstmp, outputfile):
        if len(self._peer_friends):
            print >> outputfile, tstmp,

            sum_can_connect_to = 0
            for peer, friends in self._peer_friends.iteritems():
                can_connect_to = 0
                if self._peer_state[peer] == "online":
                    for friend in friends:
                        if self._peer_state[friend] == "online":
                            can_connect_to += 1

                    if len(friends):
                        can_connect_to /= float(len(friends))

                # print >> outputfile, peer, can_connect_to,
                sum_can_connect_to += can_connect_to

            print >> outputfile, "average", sum_can_connect_to / float(len(self._peer_friends))


def main(inputfile, outputfile):
    inputfile = os.path.abspath(inputfile)
    if os.path.exists(inputfile):
        f = open(outputfile, 'w')

        ChurnAnalyzer(inputfile, f)

        f.close()
    else:
        print >> sys.stderr, inputfile, "not found"

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s <input-file> <output-file>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    main(sys.argv[1], sys.argv[2])
