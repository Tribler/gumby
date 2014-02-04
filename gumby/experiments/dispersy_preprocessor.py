import os
import sys
from random import expovariate, random, randint
from gumby.scenario import ScenarioRunner

class ScenarioPreProcessor(ScenarioRunner):

    def __init__(self, filename, outputfile=sys.stdout, max_tstmp=0):
        ScenarioRunner.__init__(self, filename)

        self._callables = {}
        self._callables['churn'] = self.churn
        self._callables['churn_pattern'] = self.churn_pattern

        print >> sys.stderr, "Looking for max_timestamp, max_peer... in %s" % filename,

        self.max_peer = 0
        for (tstmp, lineno, clb, args) in self._parse_scenario(filename):
            max_tstmp = max(tstmp, max_tstmp)

        print >> sys.stderr, "\tfound %d and %d" % (max_tstmp, self.max_peer)

        _max_peer = self.max_peer
        print >> sys.stderr, "Preprocessing file...",
        for (tstmp, lineno, clb, args) in self._parse_scenario(filename):

            print >> outputfile, self.file_buffer[1][lineno - 1][1]
            if clb in self._callables:
                for peer in self.yes_peers:
                    for line in self._callables[clb](tstmp, max_tstmp, *args):
                        print >> outputfile, line, '{%s}' % peer
        print >> sys.stderr, "\tdone"

    def _parse_for_this_peer(self, peerspec):
        if peerspec:
            self.yes_peers, self.no_peers = self._parse_peerspec(peerspec)
            self.max_peer = max(self.max_peer, max(self.yes_peers))
        else:
            self.yes_peers = set()
            self.no_peers = set()

        if not self.yes_peers:
            self.yes_peers = set(range(1, self.max_peer + 1))
        for peer in self.no_peers:
            self.yes_peers.discard(peer)

        return True

    def churn(self, tstmp, max_tstmp, churn_type, desired_mean=300, min_online=5.0):
        desired_mean = float(desired_mean)
        min_online = float(min_online)

        def get_delay(step):
            if churn_type == 'expon':
                return min_online + expovariate(1.0 / (desired_mean - min_online))
            elif churn_type == 'fixed':
                if step == 1:
                    return randint(min_online, desired_mean)
                return desired_mean
            else:
                raise NotImplementedError('only expon churn is implemented, got %s' % churn_type)

        go_online = random() < 0.5
        step = 1
        while tstmp < max_tstmp:
            yield "@0:%d %s" % (tstmp, "online" if go_online else "offline")
            tstmp += get_delay(step)
            go_online = not go_online
            step += 1

    def churn_pattern(self, tstmp, max_tstmp, pattern, min_online=5.0):
        pattern = [online / 100.0 for online in map(float, pattern.split(','))]
        min_online = float(min_online)

        i = 0
        prev_state = None
        while tstmp < max_tstmp:
            go_online = random() < pattern[i]
            i = (i + 1) % len(pattern)

            if go_online != prev_state:
                yield "@0:%d %s" % (tstmp, "online" if go_online else "offline")
                prev_state = go_online

            tstmp += min_online


def main(inputfile, outputfile, maxtime=0):
    inputfile = os.path.abspath(inputfile)
    if os.path.exists(inputfile):
        f = open(outputfile, 'w')

        ScenarioPreProcessor(inputfile, f, maxtime)

        f.close()
    else:
        print >> sys.stderr, inputfile, "not found"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: %s <input-file> <output-file> (<max-time>)" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    if len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
    else:
        main(sys.argv[1], sys.argv[2])
