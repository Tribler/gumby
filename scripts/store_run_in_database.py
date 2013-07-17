#!/usr/bin/env python
'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to summary csv file
@arg2: revision
@arg3: testcase name
'''

import sys
import os
from spectraperf.performanceprofile import *
from spectraperf.databasehelper import *

if __name__ == '__main__':

    DATABASE = os.path.abspath("../database/performance.db")

    if len(sys.argv) < 4:
        print "Usage: python store_run_in_database.py csvPath revision testcase"
        sys.exit(0)

    csvPath = sys.argv[1]
    revision = sys.argv[2]
    testcase = sys.argv[3]

    if not os.path.isfile(csvPath):
        print "Not a valid CSV file"
        sys.exit(0)

    if not os.path.isfile(DATABASE):
        dbHelper = InitDatabase(DATABASE)

    helper = SessionHelper(DATABASE)
    sess1 = helper.loadSessionFromCSV(revision, testcase, csvPath)
    helper.storeInDatabase(sess1)
