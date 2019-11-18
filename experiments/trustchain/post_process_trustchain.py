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
        self.do_cleanup = False
        if os.getenv('CLEAN_UP'):
            self.do_cleanup = bool(os.getenv('CLEAN_UP'))

    def aggregate_databases(self):
        aggregation_path = os.path.join(os.environ['PROJECT_DIR'], 'output', 'sqlite')
        if not os.path.exists(aggregation_path):
            os.makedirs(aggregation_path)

        self.aggregator.combine_databases()

    def aggregate_transactions(self):
        prefix = os.path.join(os.environ['PROJECT_DIR'], 'output')
        postfix = 'leader_blocks_time_'
        index = 1

        block_stat_file = os.path.join(prefix, postfix + "agg.csv")
        with open(block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', 'type', 'seq_num', 'peer_ids', 'seen_by'])
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
                            peer_ids = (row[5], row[6])
                            writer.writerow(
                                {"time": row[0], 'transaction': row[1], 'type': type_val,
                                 'seq_num': seq_num, 'peer_ids': peer_ids, 'seen_by': index})
                if self.do_cleanup:
                    os.remove(os.path.join(prefix, postfix + str(index) + '.csv'))
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
        tx_ops = dict()
        tx_stats = dict()
        min_time = None
        max_time = None
        tx_map = dict()
        seen_by_map = dict()
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
                    seen_by = int(row[-1])  # seen_by by peer
                    type_val = row[2]
                    seq_num_tuple = ast.literal_eval(row[3])  # seq_num, link_num
                    peer_ids = ast.literal_eval(row[4])  # from_peer, to_peer

                    tx = ast.literal_eval(row[1])
                    if 'mint_proof' in tx:
                        continue
                    if 'proof' in tx:
                        # Tx with/without proofs are the same
                        del tx['proof']
                    if 'condition' in tx:
                        del tx['total_spend']

                    if str(tx) not in tx_map:
                        tx_map[str(tx)] = index
                        index += 1

                    tx_map_ind = tx_map[str(tx)]
                    # The peer that initiated the transaction
                    from_peer = int(tx['peer']) if 'peer' in tx else int(tx['from_peer'])
                    # The peer that should receive the transaction
                    to_peer = int(tx['to_peer']) if 'to_peer' in tx else None
                    # When it was claimed - seq number
                    tx_id = str(tx_map_ind) + str(peer_ids) + str(seq_num_tuple)

                    # Calculate the total runtime
                    if not min_time or time < min_time:
                        min_time = time
                    if not max_time or time > max_time:
                        max_time = time
                    # Transaction seen by how many times
                    if tx_map_ind not in tx_stats:
                        tx_stats[tx_map_ind] = dict()
                    if tx_map_ind not in tx_ops:
                        tx_ops[tx_map_ind] = {tx_id}
                    else:
                        tx_ops[tx_map_ind].add(tx_id)

                        # Init peer info
                    if seen_by not in peer_counts:
                        peer_counts[seen_by] = {"from_count": 0, "to_count": 0, "others": 0}

                    if from_peer == seen_by:
                        # If this is a source operation
                        peer_counts[seen_by]["from_count"] += 1
                        if int(seq_num_tuple[1]) == 0 and 'first_create' not in tx_stats[tx_map_ind]:
                            # This is creation block
                            tx_stats[tx_map_ind]['first_create'] = time
                        elif int(seq_num_tuple[1]) != 0 and 'round_time' not in tx_stats[tx_map_ind]:
                            # The source peer sees the claim confirmation
                            tx_stats[tx_map_ind]['round_time'] = time
                    elif to_peer == seen_by:
                        # Dest operation
                        peer_counts[seen_by]["to_count"] += 1
                        if int(seq_num_tuple[1]) == 0 and 'first_seen' not in tx_stats[tx_map_ind]:
                            # Spend first seen by the counterparty
                            tx_stats[tx_map_ind]['first_seen'] = time
                        elif int(seq_num_tuple[1]) != 0 and 'claim_time' not in tx_stats[tx_map_ind]:
                            # The transaction claimed
                            tx_stats[tx_map_ind]['claim_time'] = time
                    else:
                        # Other operations seen
                        peer_counts[seen_by]["others"] += 1
                        if 'last_time' not in tx_stats[tx_map_ind]:
                            tx_stats[tx_map_ind]['last_time'] = time
                            seen_by_map[tx_map_ind] = {seen_by}
                        elif seen_by not in seen_by_map[tx_map_ind] and tx_stats[tx_map_ind]['last_time'] < time:
                            tx_stats[tx_map_ind]['last_time'] = time
        if self.do_cleanup:
            os.remove(f_name)

        import math
        import statistics as np

        total_run = max_time
        if os.getenv('TOTAL_RUN'):
            total_run = float(os.getenv('TOTAL_RUN'))

        latency_round = []
        latency_all = []
        throughput = {l: 0 for l in range(int(max_time) + 1)}
        errs = 0
        failed = 0
        ops = []

        for t in tx_stats:
            if 'round_time' not in tx_stats[t]:
                # The confirmation was never seen by the source
                failed += 1
            else:
                val = tx_stats[t]
                if 'first_seen' not in val:
                    # The transaction was not seen by the counterparty
                    errs += 1
                    continue
                round_trip = abs(val['round_time'] - val['first_create'])
                latency_round.append(round_trip)
                throughput[math.floor(val['round_time'])] += 1
                if 'last_time' not in val:
                    val['last_time'] = val['round_time']
                all_seen = abs(val['last_time'] - val['first_seen'])
                latency_all.append(all_seen)
                ops.append(len(tx_ops[t]))

        thrg = {x: y for x, y in throughput.items() if y and x < total_run+1}

        # Write performance results in a file
        res_file = os.path.join(prefix, "perf_results.txt")
        with open(res_file, 'w') as w_file:
            w_file.write("Total txs: %d\n" % len(tx_stats))
            w_file.write("Number of peers: %d\n" % len(peer_counts))
            w_file.write("Total round time: %f\n" % (max_time - min_time))
            w_file.write("\n")

            if os.getenv('TX_SEC'):
                value = 1 / float(os.getenv('TX_SEC'))
                w_file.write("System transaction rate: %d\n" % (len(peer_counts) * value))
            if os.getenv('IB_FANOUT'):
                value = int(os.getenv('IB_FANOUT'))
                w_file.write("Peer fanout: %d\n" % value)

            w_file.write("Peak throughput: %d\n" % max(thrg.values()))
            w_file.write("Avg throughput: %d\n" % np.mean(thrg.values()))
            w_file.write("St dev throughput: %d\n" % np.stdev(thrg.values()))
            w_file.write("Min throughput: %d\n" % min(thrg.values()))
            w_file.write("\n")

            w_file.write("Median operations per transaction: %d\n" % np.median(ops))
            w_file.write("Min operations per transaction: %d\n" % min(ops))
            w_file.write("Max operations per transaction: %d\n" % max(ops))
            w_file.write("\n")

            w_file.write("Min round latency: %f\n" % min(latency_round))
            w_file.write("Mean round latency: %f\n" % np.mean(latency_round))
            w_file.write("St dev round latency: %f\n" % np.stdev(latency_round))
            w_file.write("Max round latency: %f\n" % max(latency_round))
            w_file.write("\n")

            w_file.write("Min other received latency: %f\n" % min(latency_all))
            w_file.write("Mean other received latency: %f\n" % np.mean(latency_all))
            w_file.write("St dev other received latency: %f\n" % np.stdev(latency_all))
            w_file.write("Max other received latency: %f\n" % max(latency_all))
            w_file.write("\n")

            w_file.write(
                "Min from ops: %d\n" % min([d['from_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Average from ops: %d\n" % np.mean([d['from_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "St dev from ops: %d\n" % np.stdev([d['from_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Max from ops: %d\n" % max([d['from_count'] for k, d in peer_counts.items()]))
            w_file.write("\n")

            w_file.write(
                "Min to ops: %d\n" % min([d['to_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Average to ops: %d\n" % np.mean([d['to_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "St dev to ops: %d\n" % np.stdev([d['to_count'] for k, d in peer_counts.items()]))
            w_file.write(
                "Max to ops: %d\n" % max([d['to_count'] for k, d in peer_counts.items()]))
            w_file.write("\n")

            w_file.write(
                "Min other ops: %d\n" % min([d['others'] for k, d in peer_counts.items()]))
            w_file.write(
                "Average other ops: %d\n" % np.mean([d['others'] for k, d in peer_counts.items()]))
            w_file.write(
                "St dev other ops: %d\n" % np.stdev([d['others'] for k, d in peer_counts.items()]))
            w_file.write(
                "Max other ops: %d\n" % max([d['others'] for k, d in peer_counts.items()]))
            w_file.write("\n")

            w_file.write("Network/Relay transactions Not seen by the counterparty: %d\n" % errs)
            w_file.write("Failed transactions/ Not seen by the source: %d\n" % failed)

    def run(self):
        self.aggregate_transactions()
        self.write_perf_results()
        self.aggregate_databases()
        self.write_blocks_to_file()
        self.aggregate_trustchain_balances()


if __name__ == "__main__":
    # cd to the output directory
    # cd to the output directory
    os.chdir(os.environ['OUTPUT_DIR'])

    parser = TrustchainStatisticsParser(sys.argv[1])
    parser.run()
