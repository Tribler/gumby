#!/usr/bin/env python
import os
import sys

from gumby.post_process_blockchain import BlockchainTransactionsParser


class HyperledgerStatisticsParser(BlockchainTransactionsParser):
    """
    Parse Hyperledger statistics.
    """

    def parse_transactions(self):
        tx_info = {}
        for peer_nr, filename, dir in self.yield_files('tx_submit_times.txt'):
            with open(filename, "r") as tx_submit_times_file:
                content = tx_submit_times_file.read()
                for line in content.split("\n"):
                    if not line:
                        continue

                    parts = line.split(",")
                    tx_id = parts[0]
                    submit_time = int(parts[1]) - self.avg_start_time
                    tx_info[tx_id] = (peer_nr, submit_time, -1)

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
                    if block_nr == 1 or block_nr == 2: # The first block contains chaincode instantiation
                        continue

                    confirm_time = int(parts[1]) - self.avg_start_time
                    tx_id = parts[3]

                    if tx_id not in tx_info:
                        print("Transaction with ID %s not made!" % tx_id)
                        continue

                    peer_id = tx_info[tx_id][0]
                    submit_time = tx_info[tx_id][1]
                    tx_info[tx_id] = (peer_id, submit_time, confirm_time)

        for tx_id, tx_info in tx_info.items():
            latency = -1
            if tx_info[2] != -1:
                latency = tx_info[2] - tx_info[1]

            self.transactions.append((tx_info[0], tx_id, tx_info[1], tx_info[2], latency))

    def run(self):
        self.parse()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = HyperledgerStatisticsParser(sys.argv[1])
parser.run()
