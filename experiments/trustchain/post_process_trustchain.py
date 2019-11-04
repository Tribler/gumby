#!/usr/bin/env python
from __future__ import print_function

import csv
import json
import os
import sys

from gumby.statsparser import StatisticsParser

from Tribler.Core.Utilities.unicode import hexlify

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
            writer = csv.DictWriter(t_file, ['time', 'transaction', 'type', 'seq_num', 'seen_by'])
            writer.writeheader()
            while os.path.exists(os.path.join(prefix, postfix + str(index) + '.csv')):
                with open(os.path.join(prefix, postfix + str(index) + '.csv')) as read_file:
                    csv_reader = csv.reader(read_file)
                    first = True
                    for row in csv_reader:
                        if first:
                            first = False
                        else:
                            type_val = row[2]
                            seq_num = (row[3], row[4])
                            writer.writerow(
                                {"time": row[0], 'transaction': row[1], 'type': type_val, 'seq_num': seq_num,
                                 'seen_by': index})
                index += 1

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
                if hexlify(block.link_public_key) not in key_map:
                    link_peer = 0
                else:
                    link_peer = key_map[hexlify(block.link_public_key)]

                if hexlify(block.public_key) not in key_map:
                    print("Public key %s cannot be mapped to a peer!" % hexlify(block.public_key))
                    continue

                peer = key_map[hexlify(block.public_key)]
                trustchain_file.write(
                    "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%d;%s;%s\n" % (
                        peer,
                        hexlify(block.public_key),
                        block.sequence_number,
                        link_peer,
                        hexlify(block.link_public_key),
                        block.link_sequence_number,
                        hexlify(block.previous_hash),
                        hexlify(block.signature),
                        hexlify(block.hash),
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
                    total_up = tc_json['total_up']
                    total_down = tc_json['total_down']
                    balance = total_up - total_down
                    balances_file.write('%s,%d,%d,%d\n' % (peer_nr, total_up, total_down, balance))

    def write_perf_results(self):
        import ast
        import csv

        prefix = os.path.join(os.environ['PROJECT_DIR'], 'output')
        postfix = 'leader_blocks_time_'
        f_name = os.path.join(prefix, postfix + "agg.csv")
        peer_counts = {}
        tx_seen = dict()
        tx_stats = dict()
        min_time = None
        max_time = None
        tx_map = dict()
        # time,transaction,type,seq_num,seen_by

        index = 0
        with open(f_name) as read_file:
            csv_reader = csv.reader(read_file)
            first = True
            for row in csv_reader:
                if first:
                    first = False
                else:
                    time = float(row[0])
                    peer_id = int(row[-1])
                    type_val = row[2]
                    seq_num_tuple = ast.literal_eval(row[3])

                    tx = ast.literal_eval(row[1])
                    if str(tx) not in tx_map:
                        tx_map[str(tx)] = index
                        index += 1

                    tx_map_ind = tx_map[str(tx)]
                    from_peer = int(tx['peer']) if 'peer' in tx else int(tx['from_peer'])
                    to_peer = int(tx['to_peer']) if 'to_peer' in tx else None
                    tx_id = str(tx_map_ind) + str(seq_num_tuple)

                    if not min_time or time < min_time:
                        min_time = time
                    if not max_time or time > max_time:
                        max_time = time

                        # Transaction seen by how many times
                    if tx_id not in tx_seen:
                        tx_seen[tx_id] = 1
                        if tx_map_ind not in tx_stats:
                            tx_stats[tx_map_ind] = dict()
                    else:
                        tx_seen[tx_id] += 1

                    # Init peer info
                    if peer_id not in peer_counts:
                        peer_counts[peer_id] = {"from_count": 0, "to_count": 0, "others": 0}

                    if from_peer == peer_id:
                        # If this is a source transaction
                        peer_counts[peer_id]["from_count"] += 1
                        if int(seq_num_tuple[1]) == 0 and 'first_create' not in tx_stats[tx_map_ind]:
                            # This is creation block
                            tx_stats[tx_map_ind]['first_create'] = time
                        elif int(seq_num_tuple[1]) != 0 and 'round_time' not in tx_stats[tx_map_ind]:
                            # The source peer sees the claim confirmation
                            tx_stats[tx_map_ind]['round_time'] = time
                    elif to_peer == peer_id:
                        # Dest transaction
                        peer_counts[peer_id]["to_count"] += 1
                        if int(seq_num_tuple[1]) == 0 and 'first_seen' not in tx_stats[tx_map_ind]:
                            # Spend first seen by the counterparty
                            tx_stats[tx_map_ind]['first_seen'] = time
                        elif int(seq_num_tuple[1]) != 0 and 'claim_time' not in tx_stats[tx_map_ind]:
                            # The transaction claimed
                            tx_stats[tx_map_ind]['claim_time'] = time
                    else:
                        # Other transactions
                        peer_counts[peer_id]["others"] += 1
                        if 'last_time' not in tx_stats[tx_map_ind]:
                            tx_stats[tx_map_ind]['last_time'] = time
                        elif tx_stats[tx_map_ind]['last_time'] < time:
                            tx_stats[tx_map_ind]['last_time'] = time
        import math
        import statistics as np

        latency_round = []
        latency_all = []
        throughput = {l: 0 for l in range(int(max_time) + 1)}
        errs = []

        for t in tx_stats:
            if 'round_time' not in tx_stats[t]:
                pass
            else:
                val = tx_stats[t]
                if 'first_seen' not in val:
                    errs.append(t)
                    continue
                round_trip = abs(val['round_time'] - val['first_create'])
                latency_round.append(round_trip)
                throughput[math.floor(val['first_seen'])] += 1
                if 'last_time' not in val:
                    val['last_time'] = val['round_time']
                all_seen = abs(val['last_time'] - val['first_seen'])
                latency_all.append(all_seen)

                if all_seen > 10:
                    print(t, tx_stats[t])

        # Write performance results in a file
        res_file = os.path.join(prefix, "perf_results.txt")
        with open(res_file, 'w') as w_file:
            w_file.write("Total txs: %d\n" % len(tx_seen))
            w_file.write("Number of peers: %d\n" % len(peer_counts))
            w_file.write("Total round time: %f\n" % (max_time - min_time))
            w_file.write("\n")
            if os.getenv('TX_SEC'):
                value = 1 / float(os.getenv('TX_SEC'))
                w_file.write("System transaction rate: %d\n" % (len(peer_counts) * value))
            if os.getenv('IB_FANOUT'):
                value = int(os.getenv('IB_FANOUT'))
                w_file.write("Peer fanout: %d\n" % value)

            w_file.write("Peak throughput: %d\n" % max(throughput.values()))
            w_file.write("Est system throughput: %f\n" % (len(tx_seen) / (max_time - min_time)))
            w_file.write("\n")
            w_file.write("Median round latency: %f\n" % np.median(latency_round))
            w_file.write("Median last received latency: %f\n" % np.median(latency_all))
            w_file.write("\n")
            w_file.write(
                "Median from transactions: %d\n" % np.median([d['from_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Median to transactions: %d\n" % np.median([d['to_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Median other transactions: %d\n" % np.median([d['others'] for k, d in peer_counts.items()]))

            w_file.write(
                "Min transaction visibility: %d\n" % min([d for k, d in tx_seen.items()]))
            w_file.write(
                "Median transaction visibility: %d\n" % np.median([d for k, d in tx_seen.items()]))
            w_file.write(
                "Max transaction visibility: %d\n" % max([d for k, d in tx_seen.items()]))

            w_file.write("Errors: %d\n" % len(errs))

    def run(self):
        self.aggregate_transactions()
        self.aggregate_databases()
        self.write_blocks_to_file()
        self.aggregate_trustchain_balances()
        self.write_perf_results()


if __name__ == "__main__":
    # cd to the output directory
    # cd to the output directory
    os.chdir(os.environ['OUTPUT_DIR'])

    parser = TrustchainStatisticsParser(sys.argv[1])
    parser.run()
