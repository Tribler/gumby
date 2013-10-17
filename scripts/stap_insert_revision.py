#!/usr/bin/env python
import sqlite3
import sys
import os
from gumby.settings import loadConfig

if len(sys.argv) < 3:
        print "Usage: python insert_revision.py configFile revision"
        sys.exit(0)

config = loadConfig(os.path.abspath(sys.argv[1]))
print "Setting database: %s " % config['spectraperf_db_path']
DATABASE = os.path.abspath(config['spectraperf_db_path'])


revision = sys.argv[2]

qry = "insert into git_log (revision) values ('%s');" % revision
conn = sqlite3.connect(DATABASE)
c = conn.cursor()
c.execute(qry)
conn.commit()
c.close()
conn.close()
