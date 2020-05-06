#!/usr/bin/env python3
import os
import sys

from gumby.statsparser import StatisticsParser


class EthereumStatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing statistics of the Ethereum experiment
    """

    def aggregate_bandwidth(self):
        total_up, total_down = 0, 0
        for _, filename, _ in self.yield_files('bandwidth.txt'):
            with open(filename) as bandwidth_file:
                parts = bandwidth_file.read().rstrip('\n').split(",")
                total_up += int(parts[0])
                total_down += int(parts[1])

        with open('total_bandwidth.log', 'w') as taxi_file:
            taxi_file.write("%s,%s,%s\n" % (total_up, total_down, (total_up + total_down) / 2))

    def parse_transactions(self):
        with open("submitted_transactions.csv", "w") as submitted_transactions_file:
            submitted_transactions_file.write("order_id,submit_time\n")
            for _, filename, _ in self.yield_files('submitted_transactions.txt'):
                with open(filename) as individual_file:
                    submitted_transactions_file.write(individual_file.read())

        with open("completed_transactions.csv", "w") as completed_transactions_file:
            completed_transactions_file.write("order_id,complete_time\n")
            for _, filename, _ in self.yield_files('order_complete_times.txt'):
                with open(filename) as individual_file:
                    completed_transactions_file.write(individual_file.read())

    def run(self):
        self.aggregate_bandwidth()
        self.parse_transactions()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = EthereumStatisticsParser(sys.argv[1])
parser.run()
