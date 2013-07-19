#!/usr/bin/env python
'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to config file
@arg2: path to summary csv file
@arg3: revision
@arg4: testcase

'''

import sys
import os
from spectraperf.databasehelper import *
from spectraperf.performanceprofile import *


if __name__ == '__main__':

    if len(sys.argv) < 5:
        print "Usage: python calculate_similarity.py configFile csvPath revision testcase"
        sys.exit(0)

    config = loadConfig(sys.argv[1])

    csvPath = sys.argv[2]
    revision = sys.argv[3]
    testcase = sys.argv[4]

    if not os.path.isfile(csvPath):
        print "Not a valid CSV file"
        sys.exit(0)

    # load profile for revision and testcase
    profileHelper = ProfileHelper(config)
    p = profileHelper.loadFromDatabase(revision, testcase)

    helper = SessionHelper(config)
    sess = helper.loadSessionFromCSV(revision, testcase, csvPath)
    sess.isTestRun = 1
    helper.storeInDatabase(sess)

    fits = p.fitsProfile(sess)

    # TODO: where should we save the similarity?
    sim = p.similarity(fits)
    metricValue = p.similarity(fits)
    helper.storeMetricInDatabase(sess, metricValue)
    print "Metric: cosine sim, value: %f" % metricValue.value
