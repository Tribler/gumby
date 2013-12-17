import os
import sys
from random import expovariate
from gumby.scenario import ScenarioRunner

class ScenarioPreProcessor(ScenarioRunner):

    def __init__(self, filename, outputfile=sys.stdout):
        self._cur_line = None

        self._callables = {}
        self._callables['churn'] = self.churn

        print >> sys.stderr, "Looking for max_timestamp, max_peer...",
        max_tstmp = max_peer = 0
        for (tstmp, lineno, clb, args, peerspec) in self._parse_scenario(filename):
            max_tstmp = max(tstmp, max_tstmp)
            if peerspec[0]:
                max_peer = max(max_peer, max(peerspec[0]))

        print >> sys.stderr, "\tfound %d and %d" % (max_tstmp, max_peer)

        print >> sys.stderr, "Preprocessing file...",
        for (tstmp, lineno, clb, args, peerspec) in self._parse_scenario(filename):
            if clb in self._callables:
                yes_peers, no_peers = peerspec
                if not yes_peers:
                    yes_peers = set(range(1, max_peer + 1))
                for peer in no_peers:
                    yes_peers.discard(peer)

                for peer in yes_peers:
                    for line in self._callables[clb](tstmp, max_tstmp, *args):
                        print >> outputfile, line, '{%s}' % peer
            else:
                print >> outputfile, self._cur_line
        print >> sys.stderr, "\tdone"

    def _parse_for_this_peer(self, peerspec):
        return True

    def _preprocess_line(self, line):
        self._cur_line = line.strip()
        return line

    def churn(self, tstmp, max_tstmp, churn_type, desired_mean=300):
        desired_mean = float(desired_mean)

        def get_delay():
            if churn_type == 'expon':
                return 5.0 + expovariate(1.0 / (desired_mean - 5))
            else:
                raise NotImplementedError('only expon churn is implemented, got %s' % churn_type)

        while tstmp < max_tstmp:
            yield "@0:%d online" % tstmp
            tstmp += get_delay()
            yield "@0:%d offline" % tstmp
            tstmp += get_delay()

def main(inputfile, outputfile):
    if os.path.exists(inputfile):
        f = open(outputfile, 'w')

        ScenarioPreProcessor(inputfile, f)

        f.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s <input-file> <output-file>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    main(sys.argv[1], sys.argv[2])
