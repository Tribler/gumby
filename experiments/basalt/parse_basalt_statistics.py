#!/usr/bin/env python3
import os
import sys

from gumby.statsparser import StatisticsParser


class BasaltStatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing statistics of the Basalt community.
    """

    def aggregate_peer_samples(self):
        """
        Aggregate the peers sampled
        """
        with open("peer_samples.csv", "w") as out_file:
            out_file.write("peer_id\n")
            for _, filename, _ in self.yield_files('peer_samples.csv'):
                with open(filename) as samples_file:
                    for peer_sample in samples_file.readlines():
                        out_file.write(peer_sample)

    def run(self):
        self.aggregate_peer_samples()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = BasaltStatisticsParser(sys.argv[1])
parser.run()
