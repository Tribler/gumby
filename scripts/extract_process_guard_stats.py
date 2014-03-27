#!/usr/bin/env python
import sys
import os
from sys import argv, exit
from collections import defaultdict

import json


def write_records(all_nodes, sum_records, output_directory, outputfile, diffoutputfile=None):
    if len(sum_records) > 0:
        all_nodes.sort()

        fp = open(os.path.join(output_directory, outputfile), 'wb')
        fp2 = open(os.path.join(output_directory, diffoutputfile), 'wb') if diffoutputfile else None

        print >> fp, 'time', ' '.join(all_nodes)
        if fp2:
            print >> fp2, 'time', ' '.join(all_nodes)

        prev_records = {}
        for time in sorted(sum_records.iterkeys()):
            print >> fp, time,
            if fp2:
                print >> fp2, time,

            nodes = sum_records[time]
            for node in all_nodes:
                value = nodes.get(node, prev_records.get(node, 0))
                print >> fp, value,

                if fp2:
                    diff = value - prev_records.get(node, 0)
                    print >> fp2, diff,

                prev_records[node] = value
            print >> fp, ''
            if fp2:
                print >> fp2, ''

        fp.close()
        if fp2:
            fp2.close()


def parse_resource_files(input_directory, output_directory, start_timestamp=None):
    def calc_diff(curtime, prevtime, curvalue, prevvalue):
        diff = curvalue - prevvalue
        diff_in_log = curtime - prevtime

        if diff_in_log:
            return float(diff) / diff_in_log
        return 0

    max_timestamp = 0

    all_pids = set()
    all_nodes = []

    stimes = {}
    utimes = {}
    vsizes = {}
    rsizes = {}
    rchars = {}
    wchars = {}
    readbytes = {}
    writebytes = {}

    prev_stimes = {}
    prev_utimes = {}
    prev_wchar = {}
    prev_rchar = {}
    prev_writebytes = {}
    prev_readbytes = {}
    prev_times = {}

    filename = 'resource_usage.log'
    for root, dirs, files in os.walk(input_directory):
        if filename in files:
            nodename = root.split('/')[-1]
            all_nodes.append(nodename)

            print >> sys.stderr, "Parsing resource_usage file %s" % (nodename + "/" + filename)

            fn_records = os.path.join(root, filename)
            if os.stat(fn_records).st_size == 0:
                print >> sys.stderr, "Empty file, skipping"
                continue
            h_records = open(fn_records)

            line = h_records.readline()
            metainfo = json.loads(line)
            sc_clk_tck = float(metainfo['sc_clk_tck'])
            pagesize = float(metainfo['pagesize'])

            for line in h_records:
                parts = line.split()

                if start_timestamp == None:
                    start_timestamp = float(parts[0])
                max_timestamp = max(max_timestamp, float(parts[0]))
                time = float(parts[0]) - start_timestamp
                pid = nodename + "_" + parts[2][1:-1] + "_" + parts[1]

                if pid not in all_pids:
                    all_pids.add(pid)

                utime = long(parts[14])
                stime = long(parts[15])

                utimes.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), utime, prev_utimes.get(pid, utime)) / sc_clk_tck
                stimes.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), stime, prev_stimes.get(pid, stime)) / sc_clk_tck
                utimes[time].setdefault(nodename, []).append(utimes[time][pid])
                stimes[time].setdefault(nodename, []).append(stimes[time][pid])

                vsize = long(parts[23])
                vsizes.setdefault(time, {})[pid] = vsize / 1048576.0
                vsizes[time].setdefault(nodename, []).append(vsizes[time][pid])

                rss = long(parts[24])
                rsizes.setdefault(time, {})[pid] = (rss * pagesize) / 1048576.0
                rsizes[time].setdefault(nodename, []).append(rsizes[time][pid])

                # delay_io_ticks = long(parts[41])
                write_bytes = long(parts[-2])
                read_bytes = long(parts[-3])

                readbytes.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), read_bytes, prev_readbytes.get(pid, read_bytes)) / 1024.0
                writebytes.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), write_bytes, prev_writebytes.get(pid, write_bytes)) / 1024.0
                readbytes[time].setdefault(nodename, []).append(readbytes[time][pid])
                writebytes[time].setdefault(nodename, []).append(writebytes[time][pid])

                # syscw = long(parts[48])
                # syscr = long(parts[47])

                wchar = long(parts[-6])
                rchar = long(parts[-7])

                rchars.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), rchar, prev_rchar.get(pid, rchar)) / 1024.0
                wchars.setdefault(time, {})[pid] = calc_diff(time, prev_times.get(pid, time), wchar, prev_wchar.get(pid, wchar)) / 1024.0
                rchars[time].setdefault(nodename, []).append(rchars[time][pid])
                wchars[time].setdefault(nodename, []).append(wchars[time][pid])

                prev_utimes[pid] = utime
                prev_stimes[pid] = stime
                prev_rchar[pid] = rchar
                prev_wchar[pid] = wchar
                prev_readbytes[pid] = read_bytes
                prev_writebytes[pid] = write_bytes
                prev_times[pid] = time

    # some sanity checks
    nr_1utime = defaultdict(int)
    warn_utime = {}
    for pid_dict in utimes.itervalues():
        for pid, utime in pid_dict.iteritems():
            if isinstance(utime, float) and utime > 0.9:
                nr_1utime[pid] += 1

            if nr_1utime[pid] > 5:
                warn_utime[pid] = max(nr_1utime[pid], warn_utime.get(pid, nr_1utime[pid]))

    for pid, times in warn_utime.iteritems():
        print >> sys.stderr, "A process with name (%s) was measured to have a utime larger than 0.9 for %d times" % (pid, times)

    # writing records
    all_pids = list(all_pids)
    write_records(all_pids, utimes, output_directory, "utimes.txt")
    write_records(all_pids, stimes, output_directory, "stimes.txt")
    write_records(all_pids, wchars, output_directory, "wchars.txt")
    write_records(all_pids, rchars, output_directory, "rchars.txt")
    write_records(all_pids, writebytes, output_directory, "writebytes.txt")
    write_records(all_pids, readbytes, output_directory, "readbytes.txt")
    write_records(all_pids, vsizes, output_directory, "vsizes.txt")
    write_records(all_pids, rsizes, output_directory, "rsizes.txt")

    # calculate sum for all nodes
    for dictionary in [utimes, stimes, wchars, rchars, vsizes, rsizes, writebytes, readbytes]:
        for time, values in dictionary.iteritems():
            for node in all_nodes:
                if node in values:
                    values[node] = sum(values[node])

    # write mean for all nodes to separate files
    write_records(all_nodes, utimes, output_directory, "utimes_node.txt")
    write_records(all_nodes, stimes, output_directory, "stimes_node.txt")
    write_records(all_nodes, wchars, output_directory, "wchars_node.txt")
    write_records(all_nodes, rchars, output_directory, "rchars_node.txt")
    write_records(all_nodes, writebytes, output_directory, "writebytes_node.txt")
    write_records(all_nodes, readbytes, output_directory, "readbytes_node.txt")
    write_records(all_nodes, vsizes, output_directory, "vsizes_node.txt")
    write_records(all_nodes, rsizes, output_directory, "rsizes_node.txt")

    print "XMIN=%d" % 0
    print "XMAX=%d" % (max_timestamp - start_timestamp)
    print "XSTART=%d" % start_timestamp

def main(input_directory, output_directory, start_time=None):
    parse_resource_files(input_directory, output_directory, start_time)

if __name__ == "__main__":
    if len(argv) < 3:
        print >> sys.stderr, "Usage: %s <input-directory> <output-directory> [<experiment start timestamp>]" % (argv[0])
        print >> sys.stderr, "Got:", argv

        exit(1)

    if len(argv) == 4:
        main(argv[1], argv[2], int(argv[3]))
    else:
        main(argv[1], argv[2])
