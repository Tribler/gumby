#!/usr/bin/env python3
import os
import sys

from gumby.statsparser import StatisticsParser


class DHTStatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing statistics of the DHT
    """

    def aggregate_dht_response_times(self):
        with open('dht_response_times.csv', 'w') as csv_fp:
            csv_fp.write('peer time operation response_time\n')
            for peer_nr, filename, dir in self.yield_files('dht.log'):
                with open(filename) as log_fp:
                    for line in log_fp.readlines():
                        ts, method, t = line.split()
                        csv_fp.write('%s %s %s %s\n' % (peer_nr, ts, method, t))

    def run(self):
        self.aggregate_dht_response_times()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = DHTStatisticsParser(sys.argv[1])
parser.run()
