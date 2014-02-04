import os
import sys
from random import expovariate, random
from gumby.scenario import ScenarioRunner
from collections import defaultdict

class ChurnAnalyzer(ScenarioRunner):

    def __init__(self, filename, outputfile=sys.stdout, max_tstmp=sys.maxint):
        ScenarioRunner.__init__(self, filename)

        self._callables = {}
        self._callables['online'] = self.online
        self._callables['offline'] = self.offline
        self._callables['add_friend'] = self.add_friend

        self._peer_state = defaultdict(lambda: "offline")
        self._peer_friends = defaultdict(list)

        self._time_online = defaultdict(lambda :[0, 0, 0, 0])
        self._prev_online = defaultdict(int)
        self._prev_offline = defaultdict(int)

        self.max_online = self.max_offline = 0

        sorted_scenario = defaultdict(list)

        prev_tstmp = -1
        for (tstmp, lineno, clb, args) in self._parse_scenario(filename):
            if clb in self._callables and tstmp < max_tstmp:
                sorted_scenario[tstmp].append((self.yes_peers, clb, args))

        tstmps = sorted_scenario.keys()
        tstmps.sort()

        for tstmp in tstmps:
            for yes_peers, clb, args in sorted_scenario[tstmp]:
                for peer in yes_peers:
                    self._callables[clb](tstmp, peer, *args)

                if prev_tstmp != tstmp:
                    self.print_connections(tstmp, outputfile)
                    prev_tstmp = tstmp

        self.print_averages(outputfile, tstmps[-1])

    def _parse_for_this_peer(self, peerspec):
        if peerspec:
            self.yes_peers, self.no_peers = self._parse_peerspec(peerspec)
        else:
            self.yes_peers = set()
            self.no_peers = set()
        return True

    def online(self, tstmp, peer):
        self._peer_state[peer] = "online"
        self._prev_online[peer] = tstmp

        been_offline = tstmp - self._prev_offline[peer]
        self._time_online[peer][1] += been_offline
        self._time_online[peer][3] += 1

        self.max_offline = max(self.max_offline, been_offline)

    def offline(self, tstmp, peer):
        self._peer_state[peer] = "offline"
        self._prev_offline[peer] = tstmp

        been_online = tstmp - self._prev_online[peer]
        self._time_online[peer][0] += been_online
        self._time_online[peer][2] += 1

        self.max_online = max(self.max_online, been_online)

    def add_friend(self, tstmp, peer, friend):
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

    def print_averages(self, outputfile, max_tstmp):
        online_time = offline_time = 0
        nr_peers = 0
        ave_on_sessions = ave_off_sessions = 0
        for on, off, nr_on_sessions, nr_off_sessions in self._time_online.values():
            if nr_on_sessions:
                online_time += on / float(nr_on_sessions)
            if nr_off_sessions:
                offline_time += off / float(nr_off_sessions)

            ave_on_sessions += nr_on_sessions
            ave_off_sessions += nr_off_sessions
            nr_peers += 1

        print >> outputfile, "average online", online_time / float(nr_peers), "offline", offline_time / float(nr_peers), nr_peers
        print >> outputfile, "average online", ave_on_sessions / float(nr_peers), "offline", ave_off_sessions / float(nr_peers), nr_peers
        print >> outputfile, "max online", self.max_online, "offline", self.max_offline

def main(inputfile, outputfile, max_tstmp=sys.maxint):
    inputfile = os.path.abspath(inputfile)
    if os.path.exists(inputfile):
        f = open(outputfile, 'w')

        ChurnAnalyzer(inputfile, f, int(max_tstmp))

        f.close()
    else:
        print >> sys.stderr, inputfile, "not found"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: %s <input-file> <output-file> (<max_tstmp>)" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
