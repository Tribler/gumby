#!/usr/bin/env python3
import json
import os
import sys

from gumby.statsparser import StatisticsParser


class IPv8StatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing generic IPv8 statistics.
    """

    def aggregate_messages(self):
        """
        Aggregate all messages sent during the experiment. For each client, we read all the written data and
        reduce the statistics to intervals of 5 second.
        """
        stats_per_peer = {}
        for peer_nr, filename, dir in self.yield_files('ipv8_statistics.txt'):
            stat_dicts = []
            with open(filename) as stats_file:
                content = stats_file.read()
                for line in content.split('\n'):
                    if not line:
                        continue
                    stat_dict = json.loads(line)
                    stat_dicts.append((stat_dict["time"], stat_dict["stats"]))

            if not stat_dicts:
                continue

            # Sort the stat_dicts on time
            stat_dicts.sort(key=lambda tup: tup[0])

            collapsed_stat_dicts = []

            # Aggregate statistics for all available overlays
            for stat_time, stat_dict in stat_dicts:
                collapsed_stat_dict = {}
                for _, msg_stats_dict in stat_dict.items():
                    for msg_id, specific_msg_stats_dict in msg_stats_dict.items():
                        if msg_id not in collapsed_stat_dict:
                            collapsed_stat_dict[msg_id] = {'num_up': 0, 'num_down': 0, 'bytes_up': 0, 'bytes_down': 0}
                        collapsed_stat_dict[msg_id]['num_up'] += specific_msg_stats_dict['num_up']
                        collapsed_stat_dict[msg_id]['num_down'] += specific_msg_stats_dict['num_down']
                        collapsed_stat_dict[msg_id]['bytes_up'] += specific_msg_stats_dict['bytes_up']
                        collapsed_stat_dict[msg_id]['bytes_down'] += specific_msg_stats_dict['bytes_down']
                collapsed_stat_dicts.append((stat_time, collapsed_stat_dict))

            stats_per_peer[peer_nr] = collapsed_stat_dicts

        # Find the largest time across all the files + different messages we have
        msg_ids = set()
        largest_time = 0
        for stat_lists in stats_per_peer.values():
            for stat_time, stat_dict in stat_lists:
                if stat_time > largest_time:
                    largest_time = stat_time
                for msg_id in stat_dict.keys():
                    msg_ids.add(msg_id)

        if not msg_ids:
            return

        # Round to multiples of five
        largest_time = int(round(largest_time / 5.0) * 5)

        # We now construct the final list
        results = []
        for ind in range(0, largest_time // 5 + 1):
            placeholder_dict = {}
            for msg_id in msg_ids:
                placeholder_dict[msg_id] = {'num_up': 0, 'num_down': 0, 'bytes_up': 0, 'bytes_down': 0}
            results.append(placeholder_dict)

        # We now actually fill in the results
        for ind in range(1, largest_time // 5 + 1):
            cur_time = ind * 5
            for stats_list in stats_per_peer.values():
                filtered_dicts = [stat_dict for stat_time, stat_dict in stats_list if stat_time <= cur_time]
                if not filtered_dicts:
                    continue
                required_dict = filtered_dicts[-1]

                # We have to merge the information now
                for msg_id, msg_stats in required_dict.items():
                    results[ind][msg_id]['num_up'] += msg_stats['num_up']
                    results[ind][msg_id]['num_down'] += msg_stats['num_down']
                    results[ind][msg_id]['bytes_up'] += msg_stats['bytes_up']
                    results[ind][msg_id]['bytes_down'] += msg_stats['bytes_down']

        # Write the information to a file
        with open(os.path.join(self.node_directory, 'ipv8_msg_stats.csv'), 'w') as output_file:
            output_file.write("time,msg_id,num_up,num_down,bytes_up,bytes_down\n")
            for ind, stats in enumerate(results):
                cur_time = ind * 5
                for msg_id, msg_stats in stats.items():
                    output_file.write("%d,%s,%d,%d,%d,%d\n" % (cur_time, msg_id, msg_stats['num_up'],
                                                               msg_stats['num_down'], msg_stats['bytes_up'],
                                                               msg_stats['bytes_down']))

    def aggregate_peer_connections(self):
        peers_connections = set()

        for peer_nr, filename, dir in self.yield_files('verified_peers.txt'):
            peer_connections = [line.rstrip('\n') for line in open(filename)]
            for peer_connection in peer_connections:
                peers_connections.add((peer_nr, int(peer_connection)))

        with open('peer_connections.log', 'w') as connections_file:
            connections_file.write("peer_a,peer_b\n")
            for peer_a, peer_b in peers_connections:
                connections_file.write("%d,%d\n" % (peer_a, peer_b))

    def aggregate_bandwidth(self):
        total_up, total_down = 0, 0
        for peer_nr, filename, dir in self.yield_files('bandwidth.txt'):
            with open(filename) as bandwidth_file:
                parts = bandwidth_file.read().rstrip('\n').split(",")
                total_up += int(parts[0])
                total_down += int(parts[1])

        with open('total_bandwidth.log', 'w') as output_file:
            output_file.write("%s,%s,%s\n" % (total_up, total_down, (total_up + total_down) / 2))

    def aggregate_autoplot(self):
        autoplot_dict = {}
        for peer_nr, filename, dir in self.yield_files('autoplot.txt'):
            with open(filename, 'r') as directive_file:
                input_filename = directive_file.readline()[:-1]
                base_dir = os.path.dirname(filename)
                while input_filename:
                    with open(os.path.join(base_dir, 'autoplot', input_filename), 'r') as autoplot_src:
                        data = autoplot_src.read()
                        existing_data = autoplot_dict.get(input_filename)
                        if existing_data:
                            autoplot_dict[input_filename] = autoplot_dict[input_filename] + data[data.find('\n')+1:]
                        else:
                            autoplot_dict[input_filename] = data
                    input_filename = directive_file.readline()[:-1]
        if not os.path.exists("autoplot"):
            os.mkdir("autoplot")
        for filename in autoplot_dict:
            with open(os.path.join('autoplot', filename), 'w') as output_file:
                output_file.write(autoplot_dict[filename])

    def aggregate_annotations(self):
        annotation_dict = {}
        peer_set = set()
        for peer_nr, filename, dir in self.yield_files('statistics.log'):
            peer_set.add(peer_nr)
            with open(filename, 'r') as annotation_file:
                lines = annotation_file.read().split('\n')
                for line in lines:
                    extracted = line.split(' ')
                    if len(extracted) == 1 or extracted[2] != 'annotate':
                        continue
                    message = " ".join(extracted[3:])
                    tuple_dict = annotation_dict.get(message, {})
                    tuple_dict[extracted[1]] = extracted[0]
                    annotation_dict[message] = tuple_dict
        with open(os.path.join(self.node_directory, "annotations.txt"), "w+") as h_annotations:
            h_annotations.write("annotation %s\n" % " ".join(map(str, sorted(peer_set))))
            for message, packed_values in annotation_dict.items():
                h_annotations.write('"%s" ' % message)
                counter = 0
                for node in sorted(packed_values.keys()):
                    h_annotations.write(packed_values.get(node, '?'))
                    if counter != len(packed_values.keys()) - 1:
                        h_annotations.write(" ")
                    counter += 1
                h_annotations.write("\n")

    def run(self):
        self.aggregate_annotations()
        self.aggregate_messages()
        self.aggregate_peer_connections()
        self.aggregate_bandwidth()
        self.aggregate_autoplot()


if __name__ == "__main__":
    # cd to the output directory
    os.chdir(os.environ['OUTPUT_DIR'])

    parser = IPv8StatisticsParser(sys.argv[1])
    parser.run()
