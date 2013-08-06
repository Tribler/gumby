#!/usr/bin/env python
'''
Created on Aug 6, 2013

@author: corpaul
'''
import sys
from spectraperf.performanceprofile import *
from spectraperf.databasehelper import InitDatabase, getDatabaseConn
from gumby.settings import loadConfig


def getNrRevisions(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "SELECT COUNT(*) AS cnt FROM profile WHERE testcase = '%s'" % testcase
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        return rows[0]['cnt']


def getNrRuns(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "SELECT COUNT(*) AS cnt FROM run WHERE testcase = '%s'" % testcase
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        return rows[0]['cnt']


def getAvgNrRunsPerRevision(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "SELECT COUNT(*)/(SELECT COUNT(*) FROM profile WHERE testcase ='%s') AS cnt \
                    FROM run where testcase = '%s'" % (testcase, testcase)
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        return rows[0]['cnt']


def getNrOkRuns(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "SELECT COUNT(*) AS cnt FROM run WHERE testcase = '%s' AND exit_code = '0'" % testcase
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        return rows[0]['cnt']


def getNrStacktracesPerRev(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "select count(*) as cnt, revision, run_id FROM monitored_value \
                    JOIN run ON run.id = monitored_value.run_id GROUP BY revision, run_id"
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        summary = {}
        for r in rows:
            rev = r['revision']
            if not rev in summary.keys():
                summary[rev] = {}
                summary[rev]['min'] = 999999999999999999999999999
                summary[rev]['max'] = 0
                summary[rev]['avg'] = r['cnt']

            summary[rev]['avg'] = (summary[rev]['avg'] + r['cnt']) / 2
            if r['cnt'] > summary[rev]['max']:
                summary[rev]['max'] = r['cnt']
            if r['cnt'] < summary[rev]['min']:
                summary[rev]['min'] = r['cnt']

        return summary

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print "Usage: python create_summary_report.py configFile testcase"
        sys.exit(0)

    config = loadConfig(sys.argv[1])
    testcase = sys.argv[2]
    conn = getDatabaseConn(config)

    nrRevisions = getNrRevisions(conn, testcase)
    print "# revisions: %d " % nrRevisions

    nrRuns = getNrRuns(conn, testcase)
    print "# runs: %d " % nrRuns

    nrRunsPerRev = getAvgNrRunsPerRevision(conn, testcase)
    print "# runs/revision (avg): %d" % nrRunsPerRev

    nrOkRuns = getNrOkRuns(conn, testcase)
    print "# runs exited OK: %d/%d" % (nrOkRuns, nrRuns)

    nrStacktracesPerRev = getNrStacktracesPerRev(conn, testcase)
    print nrStacktracesPerRev


