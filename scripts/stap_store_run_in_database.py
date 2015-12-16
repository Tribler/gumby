#!/usr/bin/env python2
'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to config file
@arg2: path to summary csv file
@arg3: revision
@arg4: testcase name
'''

import sys
import os
from gumby.settings import loadConfig
from gumby.spectraperf.performanceprofile import SessionHelper

if __name__ == '__main__':

    if len(sys.argv) < 5:
        print "Usage: python store_run_in_database.py configFile csvPath revision testcase"
        sys.exit(0)

    config = loadConfig(os.path.abspath(sys.argv[1]))

    # DATABASE = os.path.abspath("../database/performance.db")
    print "Setting database: %s " % config['spectraperf_db_path']
    DATABASE = os.path.abspath(config['spectraperf_db_path'])

    csvPath = sys.argv[2]
    revision = sys.argv[3]
    testcase = sys.argv[4]

    if not os.path.isfile(csvPath):
        print "Not a valid CSV file"
        sys.exit(0)

    helper = SessionHelper(config)
    sess1 = helper.loadSessionFromCSV(revision, testcase, csvPath)
    helper.appendData(sess1, csvPath.replace("summary_per_stacktrace.csv", "summary.txt"))
    helper.storeInDatabase(sess1)
    print "Run stored"
