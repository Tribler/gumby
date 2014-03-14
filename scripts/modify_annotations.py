#!/usr/bin/env python
import sys
import os

def main(input_directory, start_timestamp):
    inputfile = os.path.join(input_directory, 'annotations.txt')
    if os.path.exists(inputfile):
        f = open(inputfile, 'r')
        lines = f.realdines()
        f.close()

        f = open(inputfile, 'w')
        for line in lines:
            parts = line.split()
            parts[2] = float(parts[2]) - start_timestamp
            if len(parts) == 4:
                parts[3] = float(float[3]) - start_timestamp

            print >> f, parts.join(" ")

        f.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <peers-directory> <experiment start timestamp>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        exit(1)

    main(sys.argv[1], int(sys.argv[2]))
