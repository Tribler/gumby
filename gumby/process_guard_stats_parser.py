#!/usr/bin/env python3
import sys
import os
from collections import defaultdict

import json


# Indices in proc(5)
# Also see http://man7.org/linux/man-pages/man5/proc.5.html
PROCFS_UTIME = 14
PROCFS_STIME = 15
PROCFS_NUM_THREADS = 20
PROCFS_VSIZE = 23
PROCFS_RSS = 24
PROCFS_RCHARS = -7       # 51 (index of last /stat item) + 1
PROCFS_WCHARS = -6       # 51 (index of last /stat item) + 2
PROCFS_READ_BYTES = -3   # 51 (index of last /stat item) + 6
PROCFS_WRITE_BYTES = -2  # 51 (index of last /stat item) + 7


def write_records(all_nodes, sum_records, output_file):
    if sum_records:
        with open(output_file, 'w') as out_file:
            print('time', ' '.join(all_nodes), file=out_file)

            prev_records = {}
            for time in sorted(sum_records.keys()):
                print(time, end=' ', file=out_file)

                nodes = sum_records[time]
                for node in all_nodes:
                    value = nodes.get(node, prev_records.get(node, 0))
                    print(value, end=' ', file=out_file)

                    prev_records[node] = value
                print('', file=out_file)


class ResourceUsageParser(object):
    """
    This class implements a resource parser.
    It scans for resource usage files and writes it in CSV format.
    """

    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.all_pids = set()
        self.all_nodes = set()

        # The stime
        self.stimes = {}
        self.utimes = {}
        self.vsizes = {}
        self.rsizes = {}
        self.rchars = {}
        self.rchars_sum = {}
        self.wchars = {}
        self.wchars_sum = {}
        self.readbytes = {}
        self.readbytes_sum = {}
        self.writebytes = {}
        self.writebytes_sum = {}
        self.threads = {}

        self.prev_stimes = {}
        self.prev_utimes = {}
        self.prev_wchar = {}
        self.prev_rchar = {}
        self.prev_writebytes = {}
        self.prev_readbytes = {}
        self.prev_times = {}
        self.prev_threads = {}

    def check_utime_sanity(self):
        """
        Check a provided utimes dictionary whether processes did not take too much utime.
        """
        nr_1utime = defaultdict(int)
        warn_utime = {}
        for pid_dict in self.utimes.values():
            for pid, utime in pid_dict.items():
                if isinstance(utime, float) and utime > 0.9:
                    nr_1utime[pid] += 1

                if nr_1utime[pid] > 5:
                    warn_utime[pid] = max(nr_1utime[pid], warn_utime.get(pid, nr_1utime[pid]))

        for pid, times in warn_utime.items():
            print("A process with name (%s) was measured to have a utime larger than 0.9 for %d times"
                  % (pid, times), file=sys.stderr)

    def parse_resource_files(self):
        def calc_diff(curtime, prevtime, curvalue, prevvalue):
            diff = curvalue - prevvalue
            diff_in_log = curtime - prevtime

            if diff_in_log:
                return float(diff) / diff_in_log
            return 0

        max_timestamp = 0

        resource_usage_fn = 'resource_usage.log'
        for root, _, files in os.walk(self.input_dir):
            if resource_usage_fn in files:
                nodename = root.split('/')[-1]
                self.all_nodes.add(nodename)

                print("Parsing resource_usage file %s" % (os.path.join(nodename, "/", resource_usage_fn)),
                      file=sys.stderr)

                resource_file_path = os.path.join(root, resource_usage_fn)
                if os.stat(resource_file_path).st_size == 0:
                    print("Empty file, skipping", file=sys.stderr)
                    continue

                with open(resource_file_path, "r") as resource_file:
                    # The first line of the resource file gives the sc_clk_tck and pagesize of the node
                    line = resource_file.readline()
                    metainfo = json.loads(line)
                    sc_clk_tck = float(metainfo['sc_clk_tck'])
                    pagesize = float(metainfo['pagesize'])
                    start_timestamp = None

                    for line in resource_file:
                        parts = line.split()

                        if start_timestamp is None:
                            start_timestamp = float(parts[0])
                        max_timestamp = max(max_timestamp, float(parts[0]))
                        cur_time = float(parts[0]) - start_timestamp
                        pid = nodename + "_" + parts[2][1:-1] + "_" + parts[1]

                        if pid not in self.all_pids:
                            self.all_pids.add(pid)

                        utime = int(parts[PROCFS_UTIME])
                        stime = int(parts[PROCFS_STIME])

                        time_diff = calc_diff(cur_time, self.prev_times.get(pid, cur_time), utime,
                                              self.prev_utimes.get(pid, utime)) / sc_clk_tck
                        self.utimes.setdefault(cur_time, {})[pid] = time_diff
                        time_diff = calc_diff(cur_time, self.prev_times.get(pid, cur_time), stime,
                                              self.prev_stimes.get(pid, stime)) / sc_clk_tck
                        self.stimes.setdefault(cur_time, {})[pid] = time_diff
                        self.utimes[cur_time].setdefault(nodename, []).append(self.utimes[cur_time][pid])
                        self.stimes[cur_time].setdefault(nodename, []).append(self.stimes[cur_time][pid])

                        vsize = int(parts[PROCFS_VSIZE])
                        self.vsizes.setdefault(cur_time, {})[pid] = vsize / 1048576.0
                        self.vsizes[cur_time].setdefault(nodename, []).append(self.vsizes[cur_time][pid])

                        num_threads = int(parts[PROCFS_NUM_THREADS])
                        self.threads.setdefault(cur_time, {})[pid] = num_threads
                        self.threads[cur_time].setdefault(nodename, []).append(self.threads[cur_time][pid])

                        rss = int(parts[PROCFS_RSS])
                        self.rsizes.setdefault(cur_time, {})[pid] = (rss * pagesize) / 1048576.0
                        self.rsizes[cur_time].setdefault(nodename, []).append(self.rsizes[cur_time][pid])

                        write_bytes = int(parts[PROCFS_WRITE_BYTES])
                        read_bytes = int(parts[PROCFS_READ_BYTES])

                        self.writebytes_sum.setdefault(cur_time, {})[pid] = write_bytes / 1024.0
                        self.writebytes_sum[cur_time].setdefault(nodename, []).append(
                            self.writebytes_sum[cur_time][pid])
                        self.readbytes_sum.setdefault(cur_time, {})[pid] = read_bytes / 1024.0
                        self.readbytes_sum[cur_time].setdefault(nodename, []).append(
                            self.readbytes_sum[cur_time][pid])

                        time_diff = calc_diff(cur_time, self.prev_times.get(pid, cur_time), read_bytes,
                                              self.prev_readbytes.get(pid, read_bytes)) / 1024.0
                        self.readbytes.setdefault(cur_time, {})[pid] = time_diff
                        time_diff = calc_diff(cur_time, self.prev_times.get(pid, cur_time), write_bytes,
                                              self.prev_writebytes.get(pid, write_bytes)) / 1024.0
                        self.writebytes.setdefault(cur_time, {})[pid] = time_diff
                        self.readbytes[cur_time].setdefault(nodename, []).append(self.readbytes[cur_time][pid])
                        self.writebytes[cur_time].setdefault(nodename, []).append(self.writebytes[cur_time][pid])

                        wchar = int(parts[PROCFS_WCHARS])
                        rchar = int(parts[PROCFS_RCHARS])

                        self.wchars_sum.setdefault(cur_time, {})[pid] = wchar / 1024.0
                        self.wchars_sum[cur_time].setdefault(nodename, []).append(self.wchars_sum[cur_time][pid])
                        self.rchars_sum.setdefault(cur_time, {})[pid] = rchar / 1024.0
                        self.rchars_sum[cur_time].setdefault(nodename, []).append(self.rchars_sum[cur_time][pid])

                        self.rchars.setdefault(cur_time, {})[pid] = calc_diff(cur_time,
                                                                              self.prev_times.get(pid, cur_time),
                                                                              rchar,
                                                                              self.prev_rchar.get(pid, rchar)) / 1024.0
                        self.wchars.setdefault(cur_time, {})[pid] = calc_diff(cur_time,
                                                                              self.prev_times.get(pid, cur_time),
                                                                              wchar,
                                                                              self.prev_wchar.get(pid, wchar)) / 1024.0
                        self.rchars[cur_time].setdefault(nodename, []).append(self.rchars[cur_time][pid])
                        self.wchars[cur_time].setdefault(nodename, []).append(self.wchars[cur_time][pid])

                        self.prev_utimes[pid] = utime
                        self.prev_stimes[pid] = stime
                        self.prev_rchar[pid] = rchar
                        self.prev_wchar[pid] = wchar
                        self.prev_readbytes[pid] = read_bytes
                        self.prev_writebytes[pid] = write_bytes
                        self.prev_times[pid] = cur_time

        self.check_utime_sanity()

        # Write all data away
        pids_list = list(self.all_pids)
        write_records(pids_list, self.utimes, os.path.join(self.output_dir, "utimes.txt"))
        write_records(pids_list, self.stimes, os.path.join(self.output_dir, "stimes.txt"))
        write_records(pids_list, self.wchars, os.path.join(self.output_dir, "wchars.txt"))
        write_records(pids_list, self.rchars, os.path.join(self.output_dir, "rchars.txt"))
        write_records(pids_list, self.wchars_sum, os.path.join(self.output_dir, "wchars_sum.txt"))
        write_records(pids_list, self.rchars_sum, os.path.join(self.output_dir, "rchars_sum.txt"))
        write_records(pids_list, self.writebytes, os.path.join(self.output_dir, "writebytes.txt"))
        write_records(pids_list, self.readbytes, os.path.join(self.output_dir, "readbytes.txt"))
        write_records(pids_list, self.writebytes_sum, os.path.join(self.output_dir, "writebytes_sum.txt"))
        write_records(pids_list, self.readbytes_sum, os.path.join(self.output_dir, "readbytes_sum.txt"))
        write_records(pids_list, self.vsizes, os.path.join(self.output_dir, "vsizes.txt"))
        write_records(pids_list, self.rsizes, os.path.join(self.output_dir, "rsizes.txt"))
        write_records(pids_list, self.threads, os.path.join(self.output_dir, "threads.txt"))

        # calculate sum for all nodes
        for dictionary in [self.utimes, self.stimes, self.wchars, self.rchars, self.wchars_sum, self.rchars_sum,
                           self.vsizes, self.rsizes, self.writebytes, self.readbytes,
                           self.writebytes_sum, self.readbytes_sum, self.threads]:
            for cur_time, values in dictionary.items():
                for node in self.all_nodes:
                    if node in values:
                        values[node] = sum(values[node])

        # write mean for all nodes to separate files
        nodes_list = list(self.all_nodes)
        write_records(nodes_list, self.utimes, os.path.join(self.output_dir, "utimes_node.txt"))
        write_records(nodes_list, self.stimes, os.path.join(self.output_dir, "stimes_node.txt"))
        write_records(nodes_list, self.wchars, os.path.join(self.output_dir, "wchars_node.txt"))
        write_records(nodes_list, self.rchars, os.path.join(self.output_dir, "rchars_node.txt"))
        write_records(nodes_list, self.wchars_sum, os.path.join(self.output_dir, "wchars_sum_node.txt"))
        write_records(nodes_list, self.rchars_sum, os.path.join(self.output_dir, "rchars_sum_node.txt"))
        write_records(nodes_list, self.writebytes, os.path.join(self.output_dir, "writebytes_node.txt"))
        write_records(nodes_list, self.readbytes, os.path.join(self.output_dir, "readbytes_node.txt"))
        write_records(nodes_list, self.writebytes_sum, os.path.join(self.output_dir, "writebytes_sum_node.txt"))
        write_records(nodes_list, self.readbytes_sum, os.path.join(self.output_dir, "readbytes_sum_node.txt"))
        write_records(nodes_list, self.vsizes, os.path.join(self.output_dir, "vsizes_node.txt"))
        write_records(nodes_list, self.rsizes, os.path.join(self.output_dir, "rsizes_node.txt"))
        write_records(nodes_list, self.threads, os.path.join(self.output_dir, "threads_node.txt"))

        with open(os.path.join(self.output_dir, "axis_stats.txt"), "w") as axis_stats_file:
            axis_stats_file.write("XMIN=0\n")
            axis_stats_file.write("XMAX=%d\n" % (max_timestamp - start_timestamp))
            axis_stats_file.write("XSTART=%d\n" % start_timestamp)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s <input-directory> <output-directory> [<experiment start timestamp>]" % (sys.argv[0]),
              file=sys.stderr)
        print("Got:", sys.argv, file=sys.stderr)

        sys.exit(1)

    parser = ResourceUsageParser(sys.argv[1], sys.argv[2])
    parser.parse_resource_files()
