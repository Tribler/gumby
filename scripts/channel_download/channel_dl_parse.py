#!/usr/bin/env python

import argparse
from collections import defaultdict


class Activity:
    def __init__(self):
        self.ts = "20161010T101010.100Z"
        self.infohash = "0" * 40
        self.id = -1

        self.ulrate = 0
        self.dlrate = 0
        self.ultotal = 0
        self.dltotal = 0
        self.progress = 0
        self.avail = 0.0
        self.dsavail = 0.0

        self.ip = "0.0.0.0:0"


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()

    infohash_set = set([])
    infohash_short_long = {}
    infohash_name = {}
    tlist = defaultdict(lambda: Activity())

    with open(args.log) as fin:
        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue

            split_msg = message.split(" ")

            if (len(split_msg) == 5 and split_msg[0] == 'Find') or split_msg[0] == 'Setup':
                infohash_set.add(split_msg[-1])
                if len(split_msg) == 5:
                    infohash_name[split_msg[-1]] = split_msg[1]

            if len(split_msg) == 12:
                try:
                    ihash_short = split_msg[1].split("=")[1][:-1]
                except IndexError:
                    # "file not found" line
                    continue

                if ihash_short not in infohash_short_long.keys():
                    for n in infohash_set:
                        if n.startswith(ihash_short):
                            infohash_short_long[ihash_short] = n
                            break

                a = Activity()
                a.ip = split_msg[0]
                a.ts = ts
                a.dlrate = int(split_msg[2].split("=")[1][:-1])
                a.ulrate = int(split_msg[3].split("=")[1][:-1])

                a.dltotal = int(split_msg[8].split("=")[1])
                a.ultotal = int(split_msg[9].split("=")[1])

                a.progress = float(split_msg[4].split("=")[1][:-1])
                a.infohash = ihash_short

                a.avail = float(split_msg[10].split("=")[1])
                a.dsavail = float(split_msg[11].split("=")[1])

                tlist[line] = a

    print "ts\tihash\tactor\tul_speed\tdl_speed\tul_tot\tdl_tot\tprogress\tavail\tdsavail"
    for _, a in tlist.items():
        print "%s\t%s\t%s\t%d\t%d\t%d\t%d\t%f\t%f\t%f\t" %(a.ts, infohash_short_long[a.infohash], a.ip, a.ulrate,
                                                           a.dlrate, a.ultotal, a.dltotal, a.progress,
                                                           a.avail, a.dsavail)

    with open('ihashname.txt', 'a') as tbl:
        for i in infohash_name.keys():
            tbl.write("%s\t%s\n" %(i, infohash_name[i]))

if __name__ == "__main__":
    main()
