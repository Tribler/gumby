#!/usr/bin/env python2
from __future__ import print_function
import re
import sys
import os

from collections import defaultdict, Iterable
from json import loads
from time import time
from traceback import print_exc

from six.moves import xrange

try:
    cmp             # Python 2
except NameError:   # Python 3
    def cmp(x, y):  # pylint: disable=redefined-builtin
        return (x > y) - (x < y)


class ExtractStatistics:

    def __init__(self, node_directory, handlers=[]):
        self.node_directory = node_directory
        self.handlers = handlers
        self.start_of_experiment = 0

    def add_handler(self, handler):
        self.handlers.append(handler)

    def parse(self):
        for handler in self.handlers:
            handler.parse(self)

        files = sorted(self.yield_files())
        if not len(files):
            print("No files found to parse!", file=sys.stderr)
            return

        print("Starting to parse", len(files), "files", file=sys.stderr)

        self.min_timeoffset = sys.maxsize
        self.max_timeoffset = 0
        self.start_of_experiment = int(self.get_first_datetime(files))

        start_time = time()
        start_size = 0
        after_size = 0
        total_size = len(files)

        for node_nr, filename, outputdir in files:
            for handler in self.handlers:
                handler.new_file(node_nr, filename, outputdir)

            for line_nr, timestamp, timeoffset, key, json in self.read(filename):
                try:
                    converted_json = None

                    # we limit the output granularity to int
                    timestamp = int(timestamp)
                    timeoffset = int(timeoffset)

                    for handler in self.handlers:
                        if handler.filter_line(node_nr, line_nr, timestamp, timeoffset, key):
                            if not converted_json:
                                try:
                                    converted_json = loads(json)
                                except:
                                    converted_json = json.strip()

                            handler.handle_line(node_nr, line_nr, timestamp, timeoffset, key, converted_json)
                except:
                    print("Error while parsing line", key, json, file=sys.stderr)
                    print_exc()

                self.min_timeoffset = min(self.min_timeoffset, timeoffset)
                self.max_timeoffset = max(self.max_timeoffset, timeoffset)

            for handler in self.handlers:
                handler.end_file(node_nr, timestamp, timeoffset)

            after_size += 1

            diff_time = time() - start_time
            if diff_time > 15:
                diff_size = after_size - start_size
                remaining_size = total_size - after_size

                if diff_size > 0:
                    avg_proc_time = diff_time / diff_size
                    remaining_time = remaining_size * avg_proc_time
                    print(remaining_size, "files or", self.elapsed_time(remaining_time),
                          "remaining (average", str(round(avg_proc_time, 2)) + 's)', file=sys.stderr)
                else:
                    print(remaining_size, "files or ? remaining", file=sys.stderr)

                start_time = time()
                start_size = after_size

        print("All files parsed, merging...", file=sys.stderr)

        for handler in self.handlers:
            handler.all_files_done(self)

        print("Finished merging", file=sys.stderr)

        print("XMIN=%d" % self.min_timeoffset)
        print("XMAX=%d" % self.max_timeoffset)
        print("XSTART=%d" % self.start_of_experiment)

    def read(self, filename, filterkey=[]):
        for line_nr, line in enumerate(open(filename)):
            timestamp, _, key, json = line.split(' ', 3)

            if not filterkey or key in filterkey:
                timestamp = float(timestamp)
                timeoffset = timestamp - self.start_of_experiment
                yield line_nr, timestamp, timeoffset, key, json

    def read_last(self, filename, chars):
        # From http://stackoverflow.com/a/260352
        f = open(filename, "r")
        f.seek(0, 2)  # Seek @ EOF
        fsize = f.tell()  # Get Size
        f.seek(max(fsize - chars, 0), 0)  # Set pos @ last n chars

        # skip broken line
        f.readline()

        lines = f.readlines()
        lines.reverse()

        for line_nr, line in enumerate(lines):
            timestamp, _, key, json = line.split(' ', 3)

            timestamp = float(timestamp)
            timeoffset = timestamp - self.start_of_experiment

            yield -line_nr, timestamp, timeoffset, key, json

    def get_first_datetime(self, files):
        datetimes = []
        for node_nr, filename, outputdir in files:
            try:
                line_nr, timestamp, timeoffset, key, json = next(self.read(filename, ['annotate', ]))
                if json.strip() == "start-experiment":
                    datetimes.append(timestamp)
            except StopIteration:
                pass
            except:
                print_exc()

        # Fallback to old method
        if not datetimes:
            print("Using fallback for get_first_datetime", file=sys.stderr)
            for node_nr, filename, outputdir in files:
                line_nr, timestamp, timeoffset, key, json = next(self.read(filename))
                datetimes.append(timestamp)

        return min(datetimes)

    def yield_files(self, file_to_check='statistics.log'):
        pattern = re.compile('[0-9]+')

        # DAS structure
        for headnode in os.listdir(self.node_directory):
            headdir = os.path.join(self.node_directory, headnode)
            if os.path.isdir(headdir):
                for node in os.listdir(headdir):
                    nodedir = os.path.join(self.node_directory, headnode, node)
                    if os.path.isdir(nodedir):
                        for peer in os.listdir(nodedir):
                            peerdir = os.path.join(self.node_directory, headnode, node, peer)
                            if os.path.isdir(peerdir) and pattern.match(peer):
                                peer_nr = int(peer)

                                filename = os.path.join(self.node_directory, headnode, node, peer, file_to_check)
                                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                                    yield peer_nr, filename, peerdir

        # localhost structure
        for peer in os.listdir(self.node_directory):
            peerdir = os.path.join(self.node_directory, peer)
            if os.path.isdir(peerdir) and pattern.match(peer):
                peer_nr = int(peer)

                filename = os.path.join(self.node_directory, peer, file_to_check)
                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                    yield peer_nr, filename, peerdir

    def merge_records(self, inputfilename, outputfilename, columnindex, diffoutputfilename=None):
        all_nodes = []

        sum_records = defaultdict(dict)
        for node_nr, _, inputdir in self.yield_files(inputfilename):
            all_nodes.append(node_nr)

            h_records = open(os.path.join(inputdir, inputfilename))
            for line in h_records:
                if line[0] == "#":
                    continue

                parts = line.split()
                if len(parts) > columnindex:
                    timestamp = float(parts[1])
                    record = parts[columnindex]

                    if record == "?":
                        continue

                    record = float(record)
                    if record == 0 and len(sum_records) == 0:
                        continue

                    sum_records[timestamp][node_nr] = record
            h_records.close()

        diffoutputfile = os.path.join(self.node_directory, diffoutputfilename) if diffoutputfilename else None
        self.write_records(all_nodes, sum_records, os.path.join(self.node_directory, outputfilename), diffoutputfile)

    def write_records(self, all_nodes, sum_records, outputfile, diffoutputfile=None):
        if len(sum_records) > 0:
            all_nodes.sort()

            fp = open(outputfile, 'wb')
            fp2 = open(diffoutputfile, 'wb') if diffoutputfile else None

            print('time', ' '.join(map(str, all_nodes)), file=fp)
            if fp2:
                print('time', ' '.join(map(str, all_nodes)), file=fp2)

            prev_records = {}
            for timestamp in sorted(sum_records.iterkeys()):
                print(timestamp, end=' ', file=fp)
                if fp2:
                    print(timestamp, end=' ', file=fp2)

                nodes = sum_records[timestamp]
                for node in all_nodes:
                    value = nodes.get(node, prev_records.get(node, "?"))
                    print(value, end=' ', file=fp)

                    if fp2:
                        prev_value = prev_records.get(node, "?")
                        if prev_value == "?":
                            prev_value = 0
                        diff = (value - prev_value) if value != "?" else 0
                        print(diff, end=' ', file=fp2)

                    prev_records[node] = value
                print('', file=fp)
                if fp2:
                    print('', file=fp2)

            fp.close()
            if fp2:
                fp2.close()

    # From http://snipplr.com/view/5713/python-elapsedtime-human-readable-time-span-given-total-seconds/
    def elapsed_time(self, seconds, suffixes=['y', 'w', 'd', 'h', 'm', 's'], add_s=False, separator=' '):
        """
        Takes an amount of seconds and turns it into a human-readable amount of time.
        """
        # the formatted time string to be returned
        time = []

        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[3], 60 * 60),
                 (suffixes[4], 60),
                 (suffixes[5], 1)]

        # for each time piece, grab the value and remaining seconds, and add it to
        # the time string
        for suffix, length in parts:
            value = int(seconds / length)
            if value > 0:
                seconds = seconds % length
                time.append('%s%s' % (str(value),
                           (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                if len(time) == 0:
                    time.append('<1s')
                break

        return separator.join(time)

class AbstractHandler(object):

    def parse(self, extract_statistics):
        pass

    def new_file(self, node_nr, filename, outputdir):
        pass

    def end_file(self, node_nr, timestamp, timeoffset):
        pass

    def all_files_done(self, extract_statistics):
        pass

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return True

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        pass

    def tuple2str(self, v):
        if isinstance(v, Iterable):
            return "-".join(map(str, v))
        if isinstance(v, float):
            return "%f" % v
        return str(v)

class BasicExtractor(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        self.dispersy_in_out = defaultdict(lambda: [0, 0, 0, 0])
        self.nr_connections = []

    def parse(self, extract_statistics):
        # determine communities
        communities = set()
        for node_nr, filename, outputdir in extract_statistics.yield_files():
            try:
                for line_nr, timestamp, timeoffset, key, json in extract_statistics.read_last(filename, 2048):
                    if 'statistics' == key:
                        json = loads(json)

                        if json.get('communities'):
                            for cid, community in json['communities'].iteritems():
                                if community.get('nr_candidates', 0):
                                    communities.add(cid)
            except:
                print_exc()

        self.communities = list(communities)
        self.communities.sort()

    def new_file(self, node_nr, filename, outputdir):
        self.c_dropped_record = 0
        self.c_communities = defaultdict(lambda: ["?", "?", "?", "?", "?"])
        self.c_blstats = defaultdict(lambda: ["?", "?", "?"])

        self.h_stat = open(os.path.join(outputdir, "stat.txt"), "w+")
        print("# timestamp timeoffset total-send total-received", file=self.h_stat)
        print("0 0 0 0", file=self.h_stat)

        self.h_drop = open(os.path.join(outputdir, "drop.txt"), "w+")
        print("# timestamp timeoffset num-drops", file=self.h_drop)
        print("0 0 0", file=self.h_drop)

        self.h_total_connections = open(os.path.join(outputdir, "total_connections.txt"), "w+")
        print("# timestamp timeoffset (num-connections +) (num-walked + ) (num-stumbled + ) "
              "(num-intro + ) (sum-incoming-connections+)", file=self.h_total_connections)
        print("#", " ".join(self.communities), file=self.h_total_connections)

        self.h_blstats = open(os.path.join(outputdir, "bl_stat.txt"), "w+")
        print("# timestamp timeoffset (bl-skip +) (bl-reuse +) (bl-new +)", file=self.h_blstats)
        print("#", " ".join(self.communities), file=self.h_blstats)

    def end_file(self, node_nr, timestamp, timeoffset):
        print(timestamp, timeoffset, self.c_dropped_record, file=self.h_drop)

        if self.c_communities.values():
            print(timestamp, timeoffset, end=' ', file=self.h_total_connections)
            for i in range(5):
                for community in self.communities:
                    print(self.c_communities[community][i], end=' ', file=self.h_total_connections)
            print('', file=self.h_total_connections)

            max_incoming_connections = max(nr_candidates[0] for nr_candidates in self.c_communities.values())
            self.nr_connections.append((max_incoming_connections, node_nr))
            self.nr_connections.sort(reverse=True)
            self.nr_connections = self.nr_connections[:10]

        self.h_stat.close()
        self.h_drop.close()
        self.h_total_connections.close()
        self.h_blstats.close()

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "statistics"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, value):
        self.dispersy_in_out[node_nr][0] = value.get("total_down", self.dispersy_in_out[node_nr][0])
        self.dispersy_in_out[node_nr][1] = value.get("total_up", self.dispersy_in_out[node_nr][1])
        self.dispersy_in_out[node_nr][2] = value.get("total_send", self.dispersy_in_out[node_nr][2])
        self.dispersy_in_out[node_nr][3] = value.get("received_count", self.dispersy_in_out[node_nr][3])

        if "total_down" in value or "total_up" in value:
            print(timestamp, timeoffset, self.dispersy_in_out[node_nr][1], self.dispersy_in_out[node_nr][0],
                  file=self.h_stat)

        if "drop_count" in value:
            self.c_dropped_record = value["drop_count"]
            print(timestamp, timeoffset, self.c_dropped_record, file=self.h_drop)

        if 'communities' in value:
            for cid, community in value['communities'].iteritems():
                self.c_communities[cid][0] = community.get('nr_candidates', self.c_communities[cid][0])
                self.c_communities[cid][1] = community.get('nr_walked', self.c_communities[cid][1])
                self.c_communities[cid][2] = community.get('nr_stumbled', self.c_communities[cid][2])
                self.c_communities[cid][3] = community.get('nr_intro', self.c_communities[cid][3])
                self.c_communities[cid][4] = community.get('total_stumbled_candidates', self.c_communities[cid][4])

                self.c_blstats[cid][0] = community.get('sync_bloom_reuse', self.c_blstats[cid][0])
                self.c_blstats[cid][1] = community.get('sync_bloom_skip', self.c_blstats[cid][1])
                self.c_blstats[cid][2] = community.get('sync_bloom_new', self.c_blstats[cid][2])

            print(timestamp, timeoffset, end=' ', file=self.h_total_connections)
            for i in range(5):
                for community in self.communities:
                    print(self.c_communities[community][i], end=' ', file=self.h_total_connections)
            print('', file=self.h_total_connections)

            print(timestamp, timeoffset, end=' ', file=self.h_blstats)
            for community in self.communities:
                print(self.c_blstats[community][0], end=' ', file=self.h_blstats)
            for community in self.communities:
                print(self.c_blstats[community][1], end=' ', file=self.h_blstats)
            for community in self.communities:
                print(self.c_blstats[community][2], end=' ', file=self.h_blstats)
            print('', file=self.h_blstats)

    def all_files_done(self, extract_statistics):
        f = open(os.path.join(extract_statistics.node_directory, "dispersy_incomming_connections.txt"), 'w')
        print("# peer max_incomming_connections", file=f)
        for nr, node in self.nr_connections:
            print(node, nr, file=f)
        f.close()

        extract_statistics.merge_records("total_record.txt", 'sum_total_records.txt', 2)
        extract_statistics.merge_records("stat.txt", 'send.txt', 2, 'send_diff.txt')
        extract_statistics.merge_records("stat.txt", 'received.txt', 3, 'received_diff.txt')
        extract_statistics.merge_records("drop.txt", 'dropped.txt', 2, 'dropped_diff.txt')

        for column in xrange(len(self.communities)):
            extract_statistics.merge_records("total_connections.txt", 'total_connections_%d.txt' % (column + 1), 2 + column)
            extract_statistics.merge_records("total_connections.txt", 'total_walked_%d.txt' % (column + 1), 2 + len(self.communities) + column)
            extract_statistics.merge_records("total_connections.txt", 'total_stumbled_%d.txt' % (column + 1), 2 + len(self.communities) + len(self.communities) + column)
            extract_statistics.merge_records("total_connections.txt", 'total_intro_%d.txt' % (column + 1), 2 + len(self.communities) + len(self.communities) + len(self.communities) + column)
            extract_statistics.merge_records("total_connections.txt", 'sum_incomming_connections_%d.txt' % (column + 1), 2 + len(self.communities) + len(self.communities) + len(self.communities) + len(self.communities) + column)

            extract_statistics.merge_records("bl_stat.txt", 'bl_reuse_%d.txt' % (column + 1), 2 + column)
            extract_statistics.merge_records("bl_stat.txt", 'bl_skip_%d.txt' % (column + 1), 2 + len(self.communities) + column)
            extract_statistics.merge_records("bl_stat.txt", 'bl_new_%d.txt' % (column + 1), 2 + len(self.communities) + len(self.communities) + column)

class SuccMessages(AbstractHandler):

    def __init__(self, messages_to_plot):
        AbstractHandler.__init__(self)

        self.dispersy_msg_distribution = {}
        self.messages_to_plot = [message for message in messages_to_plot.split(',') if message.strip()]

    def new_file(self, node_nr, filename, outputdir):
        self.c_received_records = {}
        self.c_created_records = {}

        self.h_received_record = open(os.path.join(outputdir, "received-record.txt"), "w+")
        print("# timestamp timeoffset num-records", file=self.h_received_record)
        print("0 0 0", file=self.h_received_record)

        self.h_created_record = open(os.path.join(outputdir, "created-record.txt"), "w+")
        print("# timestamp timeoffset num-records", file=self.h_created_record)
        print("0 0 0", file=self.h_created_record)

        self.h_total_record = open(os.path.join(outputdir, "total_record.txt"), "w+")
        print("# timestamp timeoffset num-records", file=self.h_total_record)
        print("0 0 0", file=self.h_total_record)

    def end_file(self, node_nr, timestamp, timeoffset):
        c_received_record = sum(self.c_received_records.itervalues())
        c_created_record = sum(self.c_created_records.itervalues())

        print(timestamp, timeoffset, c_received_record, file=self.h_received_record)
        print(timestamp, timeoffset, c_created_record, file=self.h_created_record)
        print(timestamp, timeoffset, c_received_record + c_created_record, file=self.h_total_record)

        self.h_received_record.close()
        self.h_created_record.close()
        self.h_total_record.close()

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "statistics-successful-messages" or key == "statistics-created-messages"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        writeTotal = False

        if key == "statistics-successful-messages":
            for key, value in json.iteritems():
                self.dispersy_msg_distribution[key] = max((value, node_nr), self.dispersy_msg_distribution.get(key, (0, node_nr)))

                if not self.messages_to_plot or key in self.messages_to_plot:
                    self.c_received_records[key] = value
                    writeTotal = True

            if writeTotal:
                c_received_record = sum(self.c_received_records.itervalues())
                print(timestamp, timeoffset, c_received_record, file=self.h_received_record)

        elif key == "statistics-created-messages":
            for key, value in json.iteritems():
                if not self.messages_to_plot or key in self.messages_to_plot:
                    self.c_created_records[key] = value
                    writeTotal = True

            if writeTotal:
                c_created_record = sum(self.c_created_records.itervalues())
                print(timestamp, timeoffset, c_created_record, file=self.h_created_record)

        if writeTotal:
            c_received_record = sum(self.c_received_records.itervalues())
            c_created_record = sum(self.c_created_records.itervalues())
            print(timestamp, timeoffset, c_received_record + c_created_record, file=self.h_total_record)

    def all_files_done(self, extract_statistics):
        h_dispersy_msg_distribution = open(os.path.join(extract_statistics.node_directory, "dispersy-msg-distribution.txt"), "w+")
        print("# msg_name count peer", file=h_dispersy_msg_distribution)
        for msg, count in self.dispersy_msg_distribution.iteritems():
            print("%s %d %s" % (msg, count[0], count[1]), file=h_dispersy_msg_distribution)
        h_dispersy_msg_distribution.close()

class StatisticMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        self.sum_records = defaultdict(lambda: defaultdict(dict))

        self.peer_peertype = defaultdict(dict)
        self.used_peertypes = set()
        self.nodes = set()

    def new_file(self, node_nr, filename, outputdir):
        self.h_statistics = open(os.path.join(outputdir, "scenario-statistics.txt"), "w+")
        print("# timestamp timeoffset key value", file=self.h_statistics)

        self.prev_peertype = ''
        self.prev_values = {}

    def end_file(self, node_nr, timestamp, timeoffset):
        for key, value in self.prev_values.iteritems():
            print(timestamp, timeoffset, key, value, file=self.h_statistics)
            self.sum_records[timeoffset][key][node_nr] = value

        self.h_statistics.close()

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "scenario-statistics" or key == "peertype"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        if key == "scenario-statistics":
            for key, value in json.iteritems():
                print(timestamp, timeoffset, key, value, file=self.h_statistics)

                self.sum_records[timeoffset][key][node_nr] = value

                self.prev_values[key] = value
                self.used_peertypes.add(self.prev_peertype)

        elif key == "peertype":
            self.prev_peertype = json
            self.peer_peertype[timeoffset][node_nr] = json

        self.nodes.add(node_nr)

    def all_files_done(self, extract_statistics):
        timestamps = sorted(self.sum_records.keys())

        if timestamps:
            recordkeys = self.sum_records[timestamps[0]].keys()

            h_sum_statistics = open(os.path.join(extract_statistics.node_directory, "sum_statistics.txt"), "w+")
            print("time", end=' ', file=h_sum_statistics)
            for peertype in self.used_peertypes:
                for recordkey in recordkeys:
                    if recordkey[-1] == "_":
                        print(recordkey[:-1] + ("-" + peertype if peertype else '') + "_",
                              end=' ', file=h_sum_statistics)
                    else:
                        print(recordkey + ("-" + peertype if peertype else ''), end=' ', file=h_sum_statistics)

            print('', file=h_sum_statistics)

            prev_value = defaultdict(lambda: defaultdict(int))
            cur_peertype = defaultdict(str)
            for timestamp in range(min(timestamps, *self.peer_peertype.keys()), max(timestamps) + 1):
                for node_nr, peertype in self.peer_peertype[timestamp].iteritems():
                    cur_peertype[node_nr] = peertype

                if timestamp in self.sum_records:
                    print(timestamp, end=' ', file=h_sum_statistics)

                    for peertype in self.used_peertypes:
                        for recordkey in recordkeys:
                            nr_nodes = 0.0
                            sum_values = 0.0
                            for node_nr in self.nodes:
                                if peertype == cur_peertype[node_nr]:
                                    nr_nodes += 1

                                    if node_nr in self.sum_records[timestamp][recordkey]:
                                        prev_value[recordkey][node_nr] = self.sum_records[timestamp][recordkey][node_nr]
                                    sum_values += prev_value[recordkey][node_nr]

                            if nr_nodes:
                                avg = sum_values / nr_nodes
                            else:
                                avg = 0
                            print(avg, end=' ', file=h_sum_statistics)

                    print('', file=h_sum_statistics)
            h_sum_statistics.close()

class DropMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)
        self.dispersy_dropped_msg_distribution = {}

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "statistics-dropped-messages"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        for key, value in json.iteritems():
            self.dispersy_dropped_msg_distribution[key] = max(
                (value, node_nr), self.dispersy_dropped_msg_distribution.get(key, (0, node_nr)))

    def all_files_done(self, extract_statistics):
        h_dispersy_dropped_msg_distribution = open(
            os.path.join(extract_statistics.node_directory, "dispersy-dropped-msg-distribution.txt"), "w+")

        print("# Shows which node dropped a message the most grouped by reason",
              file=h_dispersy_dropped_msg_distribution)
        print("# count nodenr msg_name", file=h_dispersy_dropped_msg_distribution)

        keys = self.dispersy_dropped_msg_distribution.keys()
        keys.sort(cmp=lambda a, b: cmp(self.dispersy_dropped_msg_distribution[a][0],
                                       self.dispersy_dropped_msg_distribution[b][0]), reverse=True)

        for msg in keys:
            count = self.dispersy_dropped_msg_distribution[msg]
            print(count[0], count[1], "'%s'" % msg, file=h_dispersy_dropped_msg_distribution)
        h_dispersy_dropped_msg_distribution.close()

class BootstrapMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)
        self.dispersy_bootstrap_distribution = defaultdict(dict)

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "statistics-bootstrap-candidates"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        for key, value in json.iteritems():
            self.dispersy_bootstrap_distribution[key][node_nr] = value

    def all_files_done(self, extract_statistics):
        h_dispersy_bootstrap_distribution = open(os.path.join(extract_statistics.node_directory, "dispersy-bootstrap-distribution.txt"), "w+")
        print("# sock_addr count", file=h_dispersy_bootstrap_distribution)

        bootstrap_keys = self.dispersy_bootstrap_distribution.keys()
        bootstrap_keys.sort(cmp=lambda a, b: cmp(sum(self.dispersy_bootstrap_distribution[a].values()), sum(self.dispersy_bootstrap_distribution[b].values())), reverse=True)
        for sock_addr in bootstrap_keys:
            nodes = self.dispersy_bootstrap_distribution[sock_addr]
            times = sum(nodes.values())
            print("%s %d" % (str(sock_addr), times), file=h_dispersy_bootstrap_distribution)
        h_dispersy_bootstrap_distribution.close()

class DebugMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        self.dispersy_debugstatistics = set()

    def new_file(self, node_nr, filename, outputdir):
        self.outputdir = outputdir

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "scenario-debug"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        for key, value in json.iteritems():
            if isinstance(value, (int, float)):
                self.write_to_debug(timestamp, timeoffset, key, value)

    def write_to_debug(self, timestamp, timeoffset, key, value):
        self.dispersy_debugstatistics.add(key)

        filename = os.path.join(self.outputdir, "scenario-%s-debugstatistics.txt" % key)
        if not os.path.exists(filename):
            h_debugstatistics = open(filename, "w+")
            print("# timestamp timeoffset value", file=h_debugstatistics)
        else:
            h_debugstatistics = open(filename, "a")

        print(timestamp, timeoffset, value, file=h_debugstatistics)
        h_debugstatistics.close()

    def all_files_done(self, extract_statistics):
        for debug_stat in self.dispersy_debugstatistics:
            extract_statistics.merge_records("scenario-%s-debugstatistics.txt" % debug_stat, "scenario-%s-debugstatistics.txt" % debug_stat, 2)

class AnnotateMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        self.annotate_dict = defaultdict(dict)
        self.nodes = []

    def new_file(self, node_nr, filename, outputdir):
        self.nodes.append(node_nr)

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "annotate"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        self.annotate_dict[json][node_nr] = timeoffset

    def all_files_done(self, extract_statistics):
        h_annotations = open(os.path.join(extract_statistics.node_directory, "annotations.txt"), "w+")
        print("annotation", " ".join(map(str, self.nodes)), file=h_annotations)
        for annotation, node_dict in self.annotate_dict.iteritems():
            print('"%s"' % annotation, end=' ', file=h_annotations)
            for node in self.nodes:
                print(node_dict.get(node, '?'), end=' ', file=h_annotations)
            print('', file=h_annotations)

def get_parser(argv):
    e = ExtractStatistics(argv[1])
    e.add_handler(BasicExtractor())
    e.add_handler(SuccMessages(argv[2] if len(argv) > 2 else ""))
    e.add_handler(StatisticMessages())
    e.add_handler(DropMessages())
    e.add_handler(BootstrapMessages())
    e.add_handler(DebugMessages())
    e.add_handler(AnnotateMessages())
    return e

if __name__ == "__main__":
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: %s <node-directory> [messagestoplot]" % (sys.argv[0]))
        print(sys.argv, file=sys.stderr)

        sys.exit(1)

    e = get_parser(sys.argv)
    e.parse()
