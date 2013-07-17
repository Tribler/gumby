#!/usr/bin/env python
'''
Created on Jul 16, 2013

@author: corpaul

@arg1: revision
@arg2: testcase

'''

import sys
import os
from spectraperf.databasehelper import *
from spectraperf.performanceprofile import *


if __name__ == '__main__':

    DATABASE = "../database/performance.db"

    if len(sys.argv) < 3:
        print "Usage: python generate_profile.py revision testcase"
        sys.exit(0)

    revision = sys.argv[1]
    testcase = sys.argv[2]

    if not os.path.isfile(DATABASE):
        dbHelper = InitDatabase(DATABASE)

    helper = SessionHelper(DATABASE)
    # load all sessions for this revision and testcase
    sessions = helper.loadFromDatabase(revision, testcase)
    if len(sessions) == 0:
        print "No sessions found."
        sys.exit(0)

    p = Profile(revision, testcase)
    for s in sessions:
        p.addSession(s)

    profileHelper = ProfileHelper(DATABASE)
    profileHelper.storeInDatabase(p)
