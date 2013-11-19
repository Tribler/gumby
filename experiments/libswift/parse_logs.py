#!/usr/bin/env python

import sys
import os

def parse_res_usage(orig, parsed=sys.stdout):
    print "Parsing resource usage file"

    try:
        sc_clk_tck = float(os.sysconf(os.sysconf_names['SC_CLK_TCK']))
        print "SC_CLK_TCK is:", sc_clk_tck
        sc_page_size = os.sysconf("SC_PAGE_SIZE")
        print "SC_PAGE_SIZE is:", sc_page_size
    except AttributeError:
        sc_clk_tck = 100.0
        sc_page_size = 4096.00
        print "SC_CLK_TCK is:", sc_clk_tck, "(default)"
        print "SC_PAGE_SIZE is:", sc_page_size, "(default)"

    for line in orig.readlines():
        parts = line.split(" ")

        timestamp = parts[0]
        utime = parts[14] # user mode time (ticks)
        stime = parts[15] # kernel mode time (ticks)
        vsize = parts[23] # virtual memory size (bytes)
        rss = parts[24] # resident set sz / #pages in mem (pages)
        rss_bytes = long(rss) * sc_page_size
        dblkio = parts[42] # agg blkio delays (ticks)

        try:
            time_diff = float(timestamp) - float(prev_timestamp)
            utime_diff = float(utime) - float(prev_utime)
            stime_diff = float(stime) - float(prev_stime)
            dblkio_diff = float(dblkio) - float(prev_dblkio)

            pcpu = ((utime_diff + stime_diff) / sc_clk_tck) * (1 / time_diff)
            delayed_blkio = (dblkio_diff / sc_clk_tck) * (1 / time_diff)
            
            print >>parsed, pcpu, vsize, rss_bytes, delayed_blkio
        except:
            time_diff = 0.0
            utime_diff = 0.0
            stime_diff = 0.0
            dblkio_diff = 0.0

        prev_timestamp = timestamp
        prev_utime = utime
        prev_stime = stime
        prev_dblkio = dblkio

def parse_speed(inp, outp):
    for line in inp.readlines():
        if line.startswith("DONE") or line.startswith("done") or line.startswith("SEED"):
            print >>outp, line[:-1]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage:", sys.argv[0], "<logs_dir>"

    logs_dir = sys.argv[1]

    res_usage = os.path.join(logs_dir, "resource_usage.log")
    with open(res_usage, "r") as o, open(res_usage + ".parsed", "w") as p:
        parse_res_usage(o, p)
    
    err_log = os.path.join(logs_dir, "00000.err")
    parsed_speed_log = os.path.join(logs_dir, "speed.parsed")
    with open(err_log, "r") as inp, open(parsed_speed_log, "w") as outp:
        parse_speed(inp, outp)
