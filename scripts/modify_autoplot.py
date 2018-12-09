#!/usr/bin/env python2
from __future__ import print_function
import sys
import os

def main(input_directory, start_timestamp):
    for filename in os.listdir(os.path.join(input_directory, 'autoplot')):
        real_filename = os.path.join(input_directory, 'autoplot', filename)
        f = open(real_filename, 'r')
        lines = f.readlines()
        f.close()

        header = False
        f = open(real_filename, 'w')
        for line in lines:
            if not header:
                f.write(line)
                header = True
                continue

            parts = line.split(',')
            parts[0] = float(parts[0]) - start_timestamp

            f.write(",".join(map(str, parts)))

        f.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <peers-directory> <experiment start timestamp>" % (sys.argv[0]))
        print(sys.argv, file=sys.stderr)

        exit(1)

    main(sys.argv[1], int(sys.argv[2]))
