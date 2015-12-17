#!/usr/bin/env python2
import sys
import os

def main(input_directory, start_timestamp):
    inputfile = os.path.join(input_directory, 'annotations.txt')
    if os.path.exists(inputfile):
        f = open(inputfile, 'r')
        lines = f.readlines()
        f.close()

        header = False
        f = open(inputfile, 'w')
        for line in lines:
            if not header:
                print >> f, line
                header = True
                continue

            parts = line.split()
            for i in range(1, len(parts)):
                parts[i] = float(parts[i]) - start_timestamp

            print >> f, " ".join(map(str, parts))

        f.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <peers-directory> <experiment start timestamp>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    main(sys.argv[1], int(sys.argv[2]))
