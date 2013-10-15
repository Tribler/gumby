#!/usr/bin/env python
'''
Created on Aug 6, 2013

@author: corpaul
'''
import sys
from gumby.settings import loadConfig
from gumby.spectraperf.databasehelper import getDatabaseConn
import numpy


def getNrRevisions(conn, testcase):
    return len(getRevisions(conn, testcase))


def getRevisions(conn, testcase):
    with conn:
        cur = conn.cursor()
        sqlCheck = "SELECT DISTINCT(revision) as rev FROM profile WHERE testcase = '%s'" % testcase
        cur.execute(sqlCheck)
        rows = cur.fetchall()
        revs = []
        for r in rows:
            revs.append(r['rev'])
        return revs


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
                summary[rev]['min'] = sys.maxint
                summary[rev]['max'] = 0
                summary[rev]['cnt'] = []
                summary[rev]['avg'] = r['cnt']

            summary[rev]['avg'] = (summary[rev]['avg'] + r['cnt']) / 2
            summary[rev]['cnt'].append(r['cnt'])
            if r['cnt'] > summary[rev]['max']:
                summary[rev]['max'] = r['cnt']
            if r['cnt'] < summary[rev]['min']:
                summary[rev]['min'] = r['cnt']

        # iterate and calculate stdev
        for rev in summary.itervalues():
            rev['std'] = numpy.std(rev['cnt'])

        return summary


def getRangePrecision(conn, testcase):
    with conn:
        cur = conn.cursor()
        sql = "SELECT stacktrace_id, AVG((max_value*1.0-min_value)/max_value) as avg, COUNT(*) as cnt \
                FROM range JOIN profile ON profile.id = profile_id WHERE testcase = '%s' \
                GROUP BY stacktrace_id ORDER BY stacktrace_id" % testcase
        cur.execute(sql)
        rows = cur.fetchall()
        return rows


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print "Usage: python create_summary_report.py configFile testcase"
        sys.exit(0)

    config = loadConfig(sys.argv[1])
    testcase = sys.argv[2]
    conn = getDatabaseConn(config)

    revisions = getRevisions(conn, testcase)
    nrRevisions = len(revisions)
    print "# revisions: %d " % nrRevisions

    nrRuns = getNrRuns(conn, testcase)
    print "# runs: %d " % nrRuns

    nrRunsPerRev = getAvgNrRunsPerRevision(conn, testcase)
    print "# runs/revision (avg): %d" % nrRunsPerRev

    nrOkRuns = getNrOkRuns(conn, testcase)
    print "# runs exited OK: %d/%d" % (nrOkRuns, nrRuns)

    nrStacktracesPerRev = getNrStacktracesPerRev(conn, testcase)

    print "# recorded stacktraces per revision \t\t min \t avg \t max \t std"

    for r in revisions:
        print "%s \t %d \t %d \t %d \t %f" % (r, nrStacktracesPerRev[r]['min'], nrStacktracesPerRev[r]['avg'], \
                                            nrStacktracesPerRev[r]['max'], nrStacktracesPerRev[r]['std'])

    rangePrecision = getRangePrecision(conn, testcase)

    print "\nRange precision"
    print "stacktrace_id \t avg (max_value-min_value)/max_value \t cnt"

    for r in rangePrecision:
        print "%s \t %f \t %d" % (r['stacktrace_id'], r['avg'], r['cnt'])
