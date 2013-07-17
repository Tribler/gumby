'''
Created on Jul 12, 2013

@author: corpaul
'''

import sqlite3


class InitDatabase(object):
    '''
    classdocs
    '''

    def __init__(self, db):
        '''
        Constructor
        '''
        print "Initializing database.. %s" % db
        self.con = sqlite3.connect(db)
        with self.con:
            self.createTables()

    def createTables(self):
        cur = self.con.cursor()

        # TODO: add keys
        cur.execute("DROP TABLE IF EXISTS profile")
        cur.execute("DROP TABLE IF EXISTS range")
        cur.execute("DROP TABLE IF EXISTS stacktrace")
        cur.execute("DROP TABLE IF EXISTS type")
        cur.execute("DROP TABLE IF EXISTS monitored_value")
        cur.execute("DROP TABLE IF EXISTS run")

        createProfile = "CREATE TABLE profile ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL);"
        cur.execute(createProfile)

        unqProfile = "CREATE UNIQUE INDEX IF NOT EXISTS profile_unq \
                            ON profile (revision, testcase)"
        cur.execute(unqProfile)

        createRange = "CREATE TABLE range ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            min_value INTEGER NOT NULL, \
                            max_value INTEGER NOT NULL, \
                            profile_id INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createRange)

        unqRange = "CREATE UNIQUE INDEX IF NOT EXISTS range_unq \
                            ON range (profile_id, stacktrace_id, type_id)"
        cur.execute(unqRange)

        createStacktrace = "CREATE TABLE stacktrace ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace TEXT NOT NULL);"
        cur.execute(createStacktrace)

        unqStacktrace = "CREATE UNIQUE INDEX IF NOT EXISTS stacktrace_unq \
                            ON stacktrace (stacktrace)"
        cur.execute(unqStacktrace)

        createStacktrace = "CREATE TABLE type ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            type TEXT NOT NULL);"
        cur.execute(createStacktrace)
        cur.execute("INSERT INTO type (type) VALUES ('BytesWritten')")

        unqType = "CREATE UNIQUE INDEX IF NOT EXISTS type_unq ON type (type)"
        cur.execute(unqType)

        createRun = "CREATE TABLE run ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL, \
                            is_test_run INTEGER NOT NULL);"
        cur.execute(createRun)

        createMonitoredValue = "CREATE TABLE monitored_value ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            value INTEGER NOT NULL, \
                            run_id INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createMonitoredValue)

        unqMonitoredValue = "CREATE UNIQUE INDEX IF NOT EXISTS \
                            monitored_value_unq \
                            ON monitored_value \
                            (stacktrace_id, run_id, type_id)"
        cur.execute(unqMonitoredValue)
