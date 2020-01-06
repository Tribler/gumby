#!/usr/bin/env python3
import os
import sys

from gumby.statsparser import StatisticsParser


class DummyStatisticsParser(StatisticsParser):
    """
    Simply read all the id.txt files and sum up the numbers inside them.
    """

    def aggregate_peer_ids(self):
        peer_id_sum = 0
        for _, filename, _ in self.yield_files('id.txt'):
            with open(filename, "r") as peer_id_file:
                read_peer_id = int(peer_id_file.read())
                peer_id_sum += read_peer_id

        with open("sum_id.txt", "w") as sum_id_file:
            sum_id_file.write("%d" % peer_id_sum)

    def run(self):
        self.aggregate_peer_ids()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = DummyStatisticsParser(sys.argv[1])
parser.run()
