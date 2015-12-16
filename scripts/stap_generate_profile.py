#!/usr/bin/env python2
'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to config file
@arg2: testcase

'''

# from gumby.spectraperf.databasehelper import getDatabaseConn
import sys
from gumby.settings import loadConfig
from gumby.spectraperf.performanceprofile import SessionHelper, Profile, ProfileHelper


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print "This script will generate the profile for a revision for a testcase."
        print "Usage: python generate_profile_batch.py configFile revision testcase"
        sys.exit(0)

    config = loadConfig(sys.argv[1])

    revision = sys.argv[2]
    testcase = sys.argv[3]

    helper = SessionHelper(config)

    # build profile
    # load all sessions for this revision and testcase
    sessions = helper.loadFromDatabase(revision, testcase)
    if len(sessions) == 0:
        print "No sessions found."
        sys.exit(0)

    p = Profile(revision, testcase, config)
    for s in sessions:
        print "adding session to profile for %s " % revision
        p.addSession(s)

    profileHelper = ProfileHelper(config)
    print "Saving profile for: %s" % revision
    profileHelper.storeInDatabase(p)
