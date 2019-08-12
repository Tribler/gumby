#!/usr/bin/env python
from __future__ import print_function

import csv
import json
import os
import sys

from gumby.statsparser import StatisticsParser
from scripts.trustchain_database_reader import GumbyDatabaseAggregator


class TrustchainStatisticsParser(StatisticsParser):
    """
    Parse TrustChain statistics after an experiment has been completed.
    """

    def __init__(self, node_directory):
        super(TrustchainStatisticsParser, self).__init__(node_directory)
        self.aggregator = GumbyDatabaseAggregator(os.path.join(os.environ['PROJECT_DIR'], 'output'))

    def aggregate_databases(self):
        aggregation_path = os.path.join(os.environ['PROJECT_DIR'], 'output', 'sqlite')
        if not os.path.exists(aggregation_path):
            os.makedirs(aggregation_path)

        self.aggregator.combine_databases()

    @staticmethod
    def aggregate_transactions():
        prefix = os.path.join(os.environ['PROJECT_DIR'], 'output')
        postfix = 'leader_blocks_time_'
        index = 1

        block_stat_file = os.path.join(prefix, postfix + "agg.csv")
        with open(block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', 'seen_by'])
            writer.writeheader()
            while os.path.exists(os.path.join(prefix, postfix + str(index) + '.csv')):
                index += 1
                with open(os.path.join(prefix, postfix + str(index) + '.csv')) as read_file:
                    csv_reader = csv.reader(read_file)
                    first = True
                    for row in csv_reader:
                        if first:
                            first = False
                        else:
                            writer.writerow({"time": row[0], 'transaction': row[1], 'seen_by': index})

    def write_blocks_to_file(self):
        # First, determine the experiment start time
        start_time = 0
        for peer_nr, filename, dir in self.yield_files('start_time.txt'):
            with open(filename) as start_time_file:
                start_time = int(float(start_time_file.read()) * 1000)
                break

        print("Writing TrustChain blocks to file")
        # Prior to writing all blocks, we construct a map from peer ID to public key
        key_map = {}
        for peer_nr, filename, dir in self.yield_files('overlays.txt'):
            with open(filename) as overlays_file:
                content = overlays_file.readlines()
                for line in content:
                    if not line:
                        continue
                    parts = line.split(',')
                    if parts[0] == 'TrustChainCommunity':
                        print("Mapping %s to peer %s" % (parts[1].rstrip(), peer_nr))
                        key_map[parts[1].rstrip()] = peer_nr

        interactions = []

        # Get all blocks
        blocks = self.aggregator.database.get_all_blocks()

        with open('trustchain.csv', 'w') as trustchain_file:
            # Write header
            trustchain_file.write(
                "peer;public_key;sequence_number;link_peer;link_public_key;"
                "link_sequence_number;previous_hash;signature;hash;type;time;time_since_start;tx\n"
            )

            # Write blocks
            for block in blocks:
                if block.link_public_key.encode('hex') not in key_map:
                    link_peer = 0
                else:
                    link_peer = key_map[block.link_public_key.encode('hex')]

                if block.public_key.encode('hex') not in key_map:
                    print("Public key %s cannot be mapped to a peer!" % block.public_key.encode('hex'))
                    continue

                peer = key_map[block.public_key.encode('hex')]
                trustchain_file.write(
                    "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%d;%s;%s\n" % (
                        peer,
                        block.public_key.encode('hex'),
                        block.sequence_number,
                        link_peer,
                        block.link_public_key.encode('hex'),
                        block.link_sequence_number,
                        block.previous_hash.encode('hex'),
                        block.signature.encode('hex'),
                        block.hash.encode('hex'),
                        block.type,
                        block.timestamp,
                        block.timestamp - start_time,
                        json.dumps(block.transaction))
                )

                if (peer, link_peer) not in interactions and (link_peer, peer) not in interactions:
                    interactions.append((peer, link_peer))

        with open('trustchain_interactions.csv', 'w') as trustchain_interactions_file:
            trustchain_interactions_file.write("peer_a,peer_b\n")
            for peer_a, peer_b in interactions:
                trustchain_interactions_file.write("%d,%d\n" % (peer_a, peer_b))

    def aggregate_trustchain_balances(self):
        with open('trustchain_balances.csv', 'w') as balances_file:
            balances_file.write('peer,total_up,total_down,balance\n')
            for peer_nr, filename, dir in self.yield_files('trustchain.txt'):
                with open(filename) as tc_file:
                    tc_json = json.loads(tc_file.read())
                    total_up = 0
                    total_down = 0
                    balance = 0
                    if 'latest_block' in tc_json and tc_json['latest_block']['type'] == 'tribler_bandwidth':
                        total_up = tc_json['latest_block']['transaction']['total_up']
                        total_down = tc_json['latest_block']['transaction']['total_down']
                        balance = total_up - total_down
                    balances_file.write('%s,%d,%d,%d\n' % (peer_nr, total_up, total_down, balance))

    def run(self):
        # self.aggregate_transactions()
        self.aggregate_databases()
        self.write_blocks_to_file()
        self.aggregate_trustchain_balances()


if __name__ == "__main__":
    # cd to the output directory
    # cd to the output directory
    os.chdir(os.environ['OUTPUT_DIR'])

    parser = TrustchainStatisticsParser(sys.argv[1])
    parser.run()
