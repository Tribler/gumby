#!/usr/bin/env python3
import os
import sys


def main(input_directory, start_timestamp):
    autoplot_dir = os.path.join(input_directory, 'autoplot')
    if not os.path.exists(autoplot_dir):
        return

    for filename in os.listdir(autoplot_dir):
        real_filename = os.path.join(autoplot_dir, filename)
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
