#!/usr/bin/env python3
import json
import os
import sys

import time
from dateutil import parser as dateparser

from gumby.post_process_blockchain import BlockchainTransactionsParser


class BitsharesStatisticsParser(BlockchainTransactionsParser):
    """
    This class is responsible for parsing statistics of Bitshares experiment
    """

    def aggregate_bandwidth(self):
        total_up, total_down = 0, 0
        for peer_nr, filename, dir in self.yield_files('bandwidth.txt'):
            with open(filename) as bandwidth_file:
                parts = bandwidth_file.read().rstrip('\n').split(",")
                total_up += int(parts[0])
                total_down += int(parts[1])

        with open('total_bandwidth.log', 'w') as taxi_file:
            taxi_file.write("%s,%s,%s\n" % (total_up, total_down, (total_up + total_down) / 2))

    def analyse_orders_on_blockchain(self):
        blocks = []
        block_timestamp_map = {}
        signature_order_map = {}
        order_fulfill_block_map = {}

        block_throughputs = []  # List of (time, num_transactions)
        for peer_nr, filename, dir in self.yield_files('blockchain.txt'):
            with open(filename) as blockchain_file:
                lines = blockchain_file.readlines()
                cur_block_num = 1
                for line in lines:
                    if not line:
                        continue
                    block = json.loads(line)
                    blocks.append(block)

                    total_ops = 0
                    # Count number of operations (excluding transfers)
                    for transaction in block["transactions"]:
                        cur_ind = 0
                        for operation in transaction["operations"]:
                            if operation[0] != 0:
                                total_ops += 1

                                if operation[0] == 1:  # If we have a new order...
                                    signature_order_map[transaction["signatures"][cur_ind]] = transaction["operation_results"][cur_ind][1]

                            cur_ind += 1

                    timestamp = time.mktime(dateparser.parse(block["timestamp"]).timetuple())
                    block_throughputs.append((timestamp, total_ops))
                    print("THROUGHPUT: %f - %s" % (timestamp, total_ops))

                    # Store the timestamp of this block
                    block_timestamp_map[cur_block_num] = timestamp * 1000 + 3600000

                    cur_block_num += 1
            break

        # Parse the account histories of users and create a map that stores the order_id with the block that captures the fulfillment
        for peer_nr, filename, dir in self.yield_files('history.txt'):
            with open(filename) as history_file:
                content = history_file.read()
                history_json = json.loads(content)
                for history_item in history_json:
                    if 'fill_order_operation' in history_item["description"]:
                        order_id = history_item["op"]["op"][1]["order_id"]
                        fulfill_block_num = history_item["op"]["block_num"]
                        order_fulfill_block_map[order_id] = fulfill_block_num

        # Find the maximum throughput per second
        max_throughput = 0
        for cur_index in range(1, len(block_throughputs)):  # Compare with the prev block every time
            cur_block = block_throughputs[cur_index]
            prev_block = block_throughputs[cur_index - 1]
            time_interval = float(cur_block[0] - prev_block[0])  # Convert to seconds
            throughput = float(cur_block[1]) / float(time_interval)
            if throughput > max_throughput:
                max_throughput = throughput

        with open("throughput.txt", "w") as throughput_file:
            throughput_file.write("%f" % max_throughput)

        # Determine individual order fulfillment times
        order_fulfill_times = {}
        avg_latency = 0
        avg_latency_count = 0
        for peer_nr, filename, dir in self.yield_files('created_orders.txt'):
            with open(filename) as created_orders_file:
                lines = created_orders_file.readlines()
                for line in lines:
                    if not line:
                        continue
                    stripped_line = line.rstrip('\n')
                    parts = stripped_line.split(',')

                    order_create_time = int(parts[0])
                    order_signature = parts[1]
                    if order_signature not in signature_order_map:
                        continue
                    order_id = signature_order_map[order_signature]

                    # We have the ID of the order now and the time it was created, find the time it was fulfilled
                    if order_id in order_fulfill_block_map:
                        fulfill_block_num = order_fulfill_block_map[order_id]
                        if fulfill_block_num in block_timestamp_map:
                            order_fulfill_time = block_timestamp_map[fulfill_block_num] - order_create_time
                            order_fulfill_times[order_id] = order_fulfill_time
                            avg_latency += order_fulfill_time
                            avg_latency_count += 1

        with open("order_fulfill_times.txt", "w") as order_fulfill_file:
            order_fulfill_file.write("order_id,time\n")
            for order_id, order_time in order_fulfill_times.items():
                order_fulfill_file.write("%s,%s\n" % (order_id, order_time))

        if avg_latency_count > 0:
            with open("latency.txt", "w") as latency_file:
                latency_file.write("%f" % (avg_latency / avg_latency_count))

    def parse_transactions(self):
        """
        Analyze all transactions on the BitShares blockchain.
        """
        signature_map = {}  # Map from signature -> block creation timestamp

        for peer_nr, filename, dir in self.yield_files('blockchain.txt'):
            with open(filename) as blockchain_file:
                lines = blockchain_file.readlines()
                cur_block_num = 1
                for line in lines:
                    if not line:
                        continue
                    block = json.loads(line)
                    timestamp = time.mktime(dateparser.parse(block["timestamp"]).timetuple()) * 1000 + 3600000

                    for transaction in block["transactions"]:
                        for signature in transaction["signatures"]:
                            signature_map[signature] = timestamp

                    cur_block_num += 1

            break  # We only need one blockchain.txt file

        # We go over all transactions created by client, check if the signature is included in the blockchain and compute the latency
        for peer_nr, filename, dir in self.yield_files('tx_submit_times.txt'):
            with open(filename) as tx_submit_times_file:
                lines = tx_submit_times_file.readlines()
                for line in lines:
                    if not line:
                        continue
                    stripped_line = line.rstrip('\n')
                    parts = stripped_line.split(',')

                    creation_time = int(parts[0]) - self.avg_start_time
                    tx_signature = parts[1]
                    latency = -1
                    confirm_time = -1
                    if tx_signature in signature_map:
                        confirm_time = signature_map[tx_signature] - self.avg_start_time
                        latency = confirm_time - creation_time

                    self.transactions.append((peer_nr, tx_signature, creation_time, confirm_time, latency))

    def run(self):
        self.aggregate_bandwidth()
        self.parse()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = BitsharesStatisticsParser(sys.argv[1])
parser.run()
