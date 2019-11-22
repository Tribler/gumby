"""
Parse the Bitshares blockchain and determine the throughput
"""
import json
import time
from dateutil import parser as dateparser

block_throughputs = []
with open("/Users/martijndevos/Downloads/blockchain.txt") as blockchain_file:
    lines = blockchain_file.readlines()
    for line in lines:
        if not line:
            continue
        block = json.loads(line)

        total_ops = 0
        # Count number of operations
        for transaction in block["transactions"]:
            total_ops += len(transaction["operations"])

        timestamp = time.mktime(dateparser.parse(block["timestamp"]).timetuple())
        block_throughputs.append((timestamp, total_ops))
        print("THROUGHPUT: %f - %s" % (timestamp, len(block["transactions"])))


# Find the maximum throughput per second
max_throughput = 0
for cur_index in range(1, len(block_throughputs)):  # Compare with the prev block every time
    cur_block = block_throughputs[cur_index]
    prev_block = block_throughputs[cur_index - 1]
    time_interval = float(cur_block[0] - prev_block[0])  # Convert to seconds
    throughput = float(cur_block[1]) / float(time_interval)
    if throughput > max_throughput:
        max_throughput = throughput

print(max_throughput)
