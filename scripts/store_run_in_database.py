'''
Created on Jul 16, 2013

@author: corpaul

@arg1: path to summary csv file
@arg2: revision
@arg3: testcase name
'''

import sys
import os
from PerformanceProfile import *
import DatabaseHelper

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python store_run_in_database.py csvPath revision testcase"
        sys.exit(0)
        
        
    csvPath = sys.argv[1]
    revision = sys.argv[2]
    testcase = sys.argv[3]
    
    
    if not os.path.isfile(csvPath):
        print "Not a valid CSV file"
        sys.exit(0)
    
    
    if not os.path.isfile("performance.db"):
        dbHelper = DatabaseHelper.InitDatabase("performance.db")
    
    helper = SessionHelper("performance.db")
    sess1 = helper.loadSessionFromCSV(revision, testcase, csvPath)
    helper.storeInDatabase(sess1)
    
    
        
        