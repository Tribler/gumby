#!/usr/bin/env python2
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
from gumby.settings import loadConfig
from gumby.spectraperf.performanceprofile import MatrixHelper, ProfileHelper, ActivityMatrix, SessionHelper
from gumby.spectraperf.performanceprofile import Type


if __name__ == '__main__':

    if len(sys.argv) < 5:
        print "Usage: python calculate_similarity.py configFile csvPath  rev(id) testcase"
        print "Note: csvPath is path to csv files, no slash at the end (TODO)"
        sys.exit(0)

    config = loadConfig(sys.argv[1])
    csvPath = sys.argv[2]
    rev = int(sys.argv[3])
    testcase = sys.argv[4]

    h = MatrixHelper(config)
    i = 0
    prevRevision = ""
    while rev != "645a7eea6919f974a1e286e163961b328e24a296":
        print "revision: %s" % rev
        prevRevision = h.getPreviousRevision(rev)
        print "previous revision: %s" % prevRevision
        print "__________________"

        # load profile for revision and testcase
        profileHelper = ProfileHelper(config)
        p = profileHelper.loadFromDatabase(prevRevision, testcase)

        if p != -1:
            output = ""

            matrix = ActivityMatrix(p.getDatabaseId(), 5, Type.BYTESWRITTEN, rev, testcase)

            for i in range(1, 6):
                helper = SessionHelper(config)
                csv = "%s/report_%s_%d/summary_per_stacktrace.csv" % (csvPath, rev, i)
                csvExtra = "%s/report_%s_%d/summary.txt" % (csvPath, rev, i)
                if not os.path.isfile(csv):
                    print "Not a valid CSV file: %s" % csv
                    continue
                sess = helper.loadSessionFromCSV(rev, testcase, csv)
                sess.isTestRun = 1
                helper.appendData(sess, csvExtra)
                helper.storeInDatabase(sess)

                fits = p.fitsProfile(sess)
                sim = p.similarity(fits)
                metricValue = p.similarity(fits)
                matrix.addFitsVector(fits)

                helper.storeMetricInDatabase(sess, metricValue)
                output += "------------------------\n%s\n" % csv
                output += "Metric: cosine sim, value: %f\n" % metricValue.value

            # print output
            matrix.calcSimilarity()

            helper = MatrixHelper(config)
            # slow but why?
            helper.storeInDatabase(matrix)

            matrix.printMatrix()

        rev = prevRevision
