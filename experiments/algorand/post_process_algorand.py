#!/usr/bin/env python
import os
import sys

from gumby.post_process_blockchain import BlockchainTransactionsParser


class AlgorandStatisticsParser(BlockchainTransactionsParser):
    """
    Parse Algorand statistics.
    """

    def parse_transactions(self):
        for peer_nr, filename, dir in self.yield_files('transactions.txt'):
            with open(filename, "r") as individual_transactions_file:
                content = individual_transactions_file.read()
                for line in content.split("\n"):
                    if not line:
                        continue

                    parts = line.split(",")
                    tx_id = parts[0]
                    submit_time = int(parts[1]) - self.avg_start_time
                    confirm_time = int(parts[2]) - self.avg_start_time

                    if confirm_time != -1:
                        tx_latency = confirm_time - submit_time
                    else:
                        tx_latency = -1

                    self.transactions.append((peer_nr, tx_id, submit_time, confirm_time, tx_latency))

    def run(self):
        self.parse()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = AlgorandStatisticsParser(sys.argv[1])
parser.run()
