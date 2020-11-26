#!/usr/bin/env python
import json
import os
import sys

from gumby.post_process_blockchain import BlockchainTransactionsParser


class EthereumStatisticsParser(BlockchainTransactionsParser):
    """
    Parse Ethereum statistics.
    """

    def parse_transactions(self):
        transactions = {}
        for peer_nr, filename, _ in self.yield_files('submit_times.txt'):
            with open(filename, "r") as individual_transactions_file:
                content = individual_transactions_file.read()
                for line in content.split("\n"):
                    if not line:
                        continue

                    parts = line.split(",")
                    tx_id = parts[0]
                    submit_time = int(parts[1]) - self.avg_start_time
                    transactions[tx_id] = [peer_nr, submit_time, -1]

        for peer_nr, filename, _ in self.yield_files('confirmed_txs.txt'):
            with open(filename, "r") as individual_transactions_file:
                content = individual_transactions_file.read()
                for line in content.split("\n"):
                    if not line:
                        continue

                    parts = line.split(",")
                    tx_id = parts[0]
                    if tx_id in transactions:
                        confirm_time = int(parts[1]) - self.avg_start_time
                        transactions[tx_id][2] = confirm_time

        for tx_id, tx_info in transactions.items():
            tx_latency = -1
            if tx_info[2] != -1:
                tx_latency = tx_info[2] - tx_info[1]
            self.transactions.append((tx_info[0], tx_id, tx_info[1], tx_info[2], tx_latency))

    def compute_avg_block_time(self):
        timestamps_sum = 0
        num_timestamps = 0
        last_timestamp = None

        for _, filename, _ in self.yield_files('blockchain.txt'):
            with open(filename, "r") as blockchain_file:
                for line in blockchain_file.readlines():
                    if not line:
                        continue

                    block = json.loads(line)
                    if not last_timestamp:
                        last_timestamp = block["timestamp"]
                    else:
                        time_between_blocks = block["timestamp"] - last_timestamp
                        timestamps_sum += time_between_blocks
                        num_timestamps += 1
                        last_timestamp = block["timestamp"]

            break  # We just need one

        # Compute the average time between blocks and write it away
        with open("avg_block_time.txt", "w") as out_file:
            out_file.write("%f" % (timestamps_sum / num_timestamps))

    def compute_avg_hash_rate(self):
        hashrate_sum = 0
        hashrate_num = 0
        for _, filename, _ in self.yield_files('hashrate.txt'):
            with open(filename, "r") as hashrate_file:
                hashrate = int(hashrate_file.read())
                hashrate_sum += hashrate
                hashrate_num += 1

        with open("avg_hashrate.txt", "w") as hashrate_file:
            hashrate_file.write("%d" % (hashrate_sum / hashrate_num))

    def run(self):
        self.parse()
        self.compute_avg_block_time()
        self.compute_avg_hash_rate()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = EthereumStatisticsParser(sys.argv[1])
parser.run()
