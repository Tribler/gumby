#!/usr/bin/env python2
'''
Created on Aug 26, 2013

@author: corpaul
'''
import unicodecsv
import sys
from gumby.settings import loadConfig


def splitFile(csv):
    var = []
    with open(csv, 'rb') as csvfile:
        reader = unicodecsv.DictReader(csvfile, delimiter=',')
        var = []
        for line in reader:
            if line['TYPE'] == "WRITE":
                var.append(line)

    with open('/tmp/tmp.csv', 'wb') as csvfile:
        fnames = ['TIMESTAMP', 'TYPE', 'TRACE', 'PROCESS', 'BYTES', 'FILE', 'TIME']
        spamwriter = unicodecsv.DictWriter(csvfile, delimiter=',', fieldnames=fnames)
        spamwriter.writerow(dict((fn, fn) for fn in fnames))
        for line in var:
            spamwriter.writerow(line)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python split_csv_files.py configFile csvFilename"
        sys.exit(0)

    config = loadConfig(sys.argv[1])
    csvFilename = sys.argv[2]

    splitFile(csvFilename)
