'''
Created on Jul 12, 2013

@author: corpaul
'''

import sqlite3
import os


class InitDatabase(object):
    '''
    classdocs
    '''

    def __init__(self, config):
        '''
        Constructor
        '''
        print "Initializing database.. %s" % config['spectraperf_db_path']
        self._config = config
        self._conn = getDatabaseConn(config, True)
        with self._conn:
            self.createTables()

    def createTables(self):
        cur = self._conn.cursor()

        # TODO: add keys
        cur.execute("DROP TABLE IF EXISTS profile")
        cur.execute("DROP TABLE IF EXISTS range")
        cur.execute("DROP TABLE IF EXISTS stacktrace")
        cur.execute("DROP TABLE IF EXISTS type")
        cur.execute("DROP TABLE IF EXISTS monitored_value")
        cur.execute("DROP TABLE IF EXISTS run")
        cur.execute("DROP TABLE IF EXISTS metric_type")
        cur.execute("DROP TABLE IF EXISTS metric_value")
        cur.execute("DROP TABLE IF EXISTS activity_matrix")
        cur.execute("DROP TABLE IF EXISTS activity_metric")

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
                            exit_code INTEGER, \
                            total_bytes INTEGER, \
                            total_actions INTEGER, \
                            is_test_run INTEGER NOT NULL);"
        cur.execute(createRun)

        createMonitoredValue = "CREATE TABLE monitored_value ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            value INTEGER NOT NULL, \
                            run_id INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL, \
                            avg_value INTEGER NOT NULL);"
        cur.execute(createMonitoredValue)

        unqMonitoredValue = "CREATE UNIQUE INDEX IF NOT EXISTS \
                            monitored_value_unq \
                            ON monitored_value \
                            (stacktrace_id, run_id, type_id)"
        cur.execute(unqMonitoredValue)

        createMetricType = "CREATE TABLE metric_type ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            metric_type TEXT NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createMetricType)
        cur.execute("INSERT INTO metric_type (metric_type, type_id) VALUES ('Similarity', 1)")

        unqMetricType = "CREATE UNIQUE INDEX IF NOT EXISTS metric_type_unq ON metric_type (metric_type, type_id)"
        cur.execute(unqMetricType)

        createMetricValue = "CREATE TABLE metric_value ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            run_id INTEGER NOT NULL, \
                            metric_type_id INTEGER NOT NULL, \
                            value REAL NOT NULL, \
                            profile_id INTEGER NOT NULL);"
        cur.execute(createMetricValue)
        unqMetricValue = "CREATE UNIQUE INDEX IF NOT EXISTS \
                            metric_value_unq \
                            ON metric_value \
                            (metric_type_id, run_id, profile_id)"
        cur.execute(unqMetricValue)

        createActivityMatrix = "CREATE TABLE activity_matrix ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL, \
                            checked_profile INTEGER NOT NULL, \
                            runs INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createActivityMatrix)

        createActivityMetric = "CREATE TABLE activity_metric ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            matrix_id INTEGER NOT NULL, \
                            value INTEGER NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            runs INTEGER NOT NULL, \
                            bytes_off INTEGER NOT NULL, \
                            range_diff INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL, \
                            calls INTEGER);"
        cur.execute(createActivityMetric)

        createGitLog = "CREATE TABLE git_log ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL);"
        cur.execute(createGitLog)


def getDatabaseConn(config, init=False):
    DATABASE = os.path.abspath(config['spectraperf_db_path'])
    initDB = False
    # if we already know we are initializing the database skip this step
    if not init and not os.path.isfile(DATABASE):
        initDB = True
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    if not init and initDB:
        InitDatabase(config)
    return con
