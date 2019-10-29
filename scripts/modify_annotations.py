#!/usr/bin/env python
from __future__ import print_function

import os
import sys


def main(input_directory, start_timestamp):
    print("Modifying annotations with start timestamp %s" % start_timestamp)
    annotations_file_path = os.path.join(input_directory, 'annotations.txt')
    if os.path.exists(annotations_file_path):
        with open(annotations_file_path, 'r') as annotations_file:
            lines = annotations_file.readlines()

        # Write the old content to another file
        with open(os.path.join(input_directory, 'old_annotations.txt'), "w") as old_annotations_file:
            old_annotations_file.writelines(lines)

        header = False
        with open(annotations_file_path, "w") as annotations_file:
            for line in lines:
                if not header:
                    annotations_file.write(line)
                    header = True
                    continue

                parts = line.split()
                for i in range(1, len(parts)):
                    parts[i] = float(parts[i]) - start_timestamp

                annotations_file.write(" ".join(map(str, parts)) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <peers-directory> <experiment start timestamp>" % (sys.argv[0]))
        print(sys.argv, file=sys.stderr)

        exit(1)

    main(sys.argv[1], int(sys.argv[2]))
