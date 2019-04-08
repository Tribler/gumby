#!/usr/bin/env python2
import os
import sys

from twisted.python import log

from gumby.statsparser import StatisticsParser
from experiments.ipv8.parse_ipv8_statistics import IPv8StatisticsParser


class DHTStatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing statistics of the DHT
    """

    def __init__(self, node_directory):
        super(DHTStatisticsParser, self).__init__(node_directory)
        self.ipv8_stats_parser = IPv8StatisticsParser(node_directory)

    def aggregate_dht_response_times(self):
        with open('dht_response_times.csv', 'w', 0) as csv_fp:
            csv_fp.write('peer time operation response_time\n')
            for peer_nr, filename, dir in self.yield_files('dht.log'):
                with open(filename) as log_fp:
                    for line in log_fp.readlines():
                        ts, method, t = line.split()
                        csv_fp.write('%s %s %s %s\n' % (peer_nr, ts, method, t))

    def run(self):
        self.aggregate_dht_response_times()
        self.ipv8_stats_parser.aggregate_annotations()
        self.ipv8_stats_parser.aggregate_autoplot()


if __name__ == '__main__':
    # cd to the output directory
    os.chdir(os.environ['OUTPUT_DIR'])

    observer = log.PythonLoggingObserver()
    observer.start()

    parser = DHTStatisticsParser(sys.argv[1])
    parser.run()
