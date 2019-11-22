#!/usr/bin/env python
import os
import sys

from gumby.post_process_blockchain import BlockchainTransactionsParser


class HyperledgerStatisticsParser(BlockchainTransactionsParser):
    """
    Parse Hyperledger statistics.
    """

    def parse_transactions(self):
        for peer_nr, filename, dir in self.yield_files('transactions.txt'):
            with open(filename, "r") as individual_transactions_file:
                content = individual_transactions_file.read()
                for line in content.split("\n"):
                    if not line:
                        continue

                    parts = line.split(",")
                    if len(parts) != 4:
                        continue

                    block_nr = int(parts[0])
                    submit_time = int(parts[2]) - self.avg_start_time
                    confirm_time = int(parts[1]) - self.avg_start_time
                    tx_id = parts[3]

                    if confirm_time != -1 and block_nr != 1 and block_nr != 2:  # The first block contains chaincode instantiation
                        tx_latency = confirm_time - submit_time
                    else:
                        tx_latency = -1

                    self.transactions.append((peer_nr, tx_id, submit_time, confirm_time, tx_latency))

    def run(self):
        self.parse()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = HyperledgerStatisticsParser(sys.argv[1])
parser.run()
