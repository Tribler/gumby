'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to summary csv file
@arg2: revision
@arg3: testcase

'''


import sys
import os
from spectraperf.databasehelper import *
from spectraperf.performanceprofile import *


if __name__ == '__main__':
    DATABASE = "../database/performance.db"

    if len(sys.argv) < 4:
        print "Usage: python calculate_similarity.py csvPath revision testcase"
        sys.exit(0)

    csvPath = sys.argv[1]
    revision = sys.argv[2]
    testcase = sys.argv[3]

    if not os.path.isfile(csvPath):
        print "Not a valid CSV file"
        sys.exit(0)

    if not os.path.isfile(DATABASE):
        dbHelper = InitDatabase(DATABASE)

    # load profile for revision and testcase
    profileHelper = ProfileHelper(DATABASE)
    p = profileHelper.loadFromDatabase(revision, testcase)

    helper = SessionHelper(DATABASE)
    sess = helper.loadSessionFromCSV(revision, testcase, csvPath)

    fits = p.fitsProfile(sess)

    # TODO: where should we save the similarity?
    print p.similarity(fits)
