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
import glob
from spectraperf.databasehelper import *
from spectraperf.performanceprofile import *


if __name__ == '__main__':

    if len(sys.argv) == 1:
        useDefault = True
    else:
        useDefault = False

    if not useDefault and len(sys.argv) < 5:
        print "Usage: python calculate_similarity.py configFile csvPath rev(id) testcase"
        sys.exit(0)

    config = loadConfig(sys.argv[1])
    csvPath = sys.argv[2]
    rev = int(sys.argv[3])
    testcase = sys.argv[4]

    while rev > 0:
        start = "%s/%s_%d_1_" % (csvPath, testcase, rev)
        end = ".csv"
        pattern = "%s*%s" % (start, end)
        result = glob.glob(pattern)
        if len(result) == 0:
            print "No profile for previous revision, exiting"
            sys.exit()
        revision = result[0][len(start):-len(end)]

        start = "%s/%s_%d_1_" % (csvPath, testcase, rev - 1)
        pattern = "%s*%s" % (start, end)
        result = glob.glob(pattern)
        if len(result) == 0:
            print "No profile for previous revision, exiting"
            sys.exit()

        prevRevision = result[0][len(start):-len(end)]
        print "Current revision: %s" % revision
        print "Previous revision: %s" % prevRevision

        # load profile for revision and testcase
        profileHelper = ProfileHelper(config)
        p = profileHelper.loadFromDatabase(prevRevision, testcase)

        output = ""

        matrix = ActivityMatrix(p.getDatabaseId(), 5, Type.BYTESWRITTEN, revision, testcase)

        for i in range(1, 6):
            helper = SessionHelper(config)
            csv = "%s/report_%d_%d/summary_per_stacktrace.csv" % (csvPath, rev, i)
            if not os.path.isfile(csv):
                print "Not a valid CSV file: %s" % csv
                continue
            sess = helper.loadSessionFromCSV(prevRevision, testcase, csv)
            sess.isTestRun = 1
            helper.storeInDatabase(sess)

            fits = p.fitsProfile(sess)
            matrix.addFitsVector(fits)

            # TODO: where should we save the similarity?
            sim = p.similarity(fits)
            metricValue = p.similarity(fits)
            helper.storeMetricInDatabase(sess, metricValue)
            output += "------------------------\n%s\n" % csv
            output += "Metric: cosine sim, value: %f\n" % metricValue.value

        print output
        matrix.calcSimilarity()

        helper = MatrixHelper(config)
        helper.storeInDatabase(matrix)

        matrix.printMatrix()
        rev = rev - 1
