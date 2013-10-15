'''
Created on Jul 4, 2013

@author: corpaul
'''
import csv
from decimal import Decimal
from math import sqrt
import sys
from gumby.spectraperf.databasehelper import getDatabaseConn
import operator


class Profile(object):
    '''
    classdocs
    '''

    def __init__(self, rev, tc, config):
        '''
        Constructor
        '''
        self.revision = rev
        self.testCase = tc
        # contains MonitoredSession objects
        # sink? we will only use the ranges
        self.runs = []
        # contains MonitoredStackRange objects
        self.ranges = {}
        self.databaseId = -1
        # self.DATABASE = DATABASE

        self._config = config
        self._conn = getDatabaseConn(config)
#        self.helper = ProfileHelper(DATABASE)

    def addSession(self, s):
        '''
        Add session s to the profile. Update ranges for all
        stacktraces in s.
        '''
        self.runs.append(s)

        for st in s.stacktraces.itervalues():
            # try with bytes/calls
            # self.addToRange(st.stacktrace, st.rawBytes)
            self.addToRange(st.stacktrace, st.avgValue)

    def addToRange(self, st, value):
        '''
        Find the range for stacktrace st and add value to it,
        i.e. extend the range if necessary.
        '''
        if st not in self.ranges:
            self.ranges[st] = MonitoredStacktraceRange(st, self._config, self._conn)
        r = self.ranges.get(st)
        # add the value
        r.addToRange(value)

    def isInRange(self, st, value):
        '''
        Returns true iff value is in the range of stacktrace st.
        '''
        assert self.getRange(st) != None, "No range set for %s" % st
        return self.getRange(st).isInRange(value)

    def getBytesOff(self, st, value):
        '''
        Returns true iff value is in the range of stacktrace st.
        '''
        assert self.getRange(st) != None, "No range set for %s" % st
        return self.getRange(st).getBytesOff(value)

    def getRange(self, st):
        return self.ranges.get(st)

    def fitsProfile(self, s):
        '''
        Returns a dict containing 1's and 0's representing whether
        the value for that stacktrace is in the range of the stacktrace
        in this profile.
        '''
        fits = {}
        for st in s.stacktraces.itervalues():
            f = {}
            r = self.getRange(st.stacktrace)
            f['bytesOff'] = st.avgValue
            if r == None:
                f['fits'] = 0
                f['rangeDiff'] = -1
            elif self.isInRange(st.stacktrace, st.avgValue):
                f['fits'] = 1
                f['bytesOff'] = 0
                f['rangeDiff'] = r.maxValue - r.minValue
            else:
                f['fits'] = 0
                f['bytesOff'] = self.getBytesOff(st.stacktrace, st.avgValue)
                f['rangeDiff'] = r.maxValue - r.minValue

            # print "Fits: %s, %.2f, %s" % (f, st.avgValue, self.getRange(st.stacktrace))
            fits[st.stacktrace] = f
            # print "bytesOff: %d / %d (%d)" % (f['bytesOff'], f['rangeDiff'], fits[st.stacktrace]['fits'])

        return fits

    def similarity(self, v):
        '''
        Returns the (simplified) cosine similarity for fit vector v
        and a vector with the same total number of items, all initialized
        to 1's.

        The rationale behind this is that we want to see how different the
        fit vector is compared to the profile (which is the fit vector with
        all 1's).

        A similarity of 1 means all elements are equal, hence all elements
        of the new vector fit in the ranges defined in the profile.

        A similarity of 0 means all elements are different, hence no elements
        fit in the defined ranges.

        A value between 0 and 1 means the vectors are partly different.
        '''
        d1 = sqrt(len(v))
        ones = 0
        for i in v.itervalues():
            ones += i['fits']
        if ones == 0:
            sim = 0
        else:
            d2 = sqrt(ones)
            sim = ones / (d1 * d2)
        metricValue = MetricValue(MetricType.COSINESIM, sim, self.getDatabaseId())
        return metricValue

    def addRange(self, range):
        if range.stacktrace in self.ranges:
            self.addToRange(range.stacktrace, range.minValue)
            self.addToRange(range.stacktrace, range.maxValue)
        self.ranges[range.stacktrace] = range

    def __str__(self):
        s = "[Profile: revision: %s, test case: %s, # runs: %d" % (self.revision, self.testCase, len(self.runs))

        for r in self.ranges.itervalues():
            s += "%s\n" % r
        return "%s]" % s

    def getDatabaseId(self):
        if self.databaseId != -1:
            return self.databaseId
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT id FROM profile WHERE revision = '%s' AND testcase = '%s'" % (self.revision, self.testCase)
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                return -1
            self.databaseId = rows[0]['id']
            return self.databaseId


class ProfileHelper(object):

    def __init__(self, config):
        self._config = config
        self._conn = getDatabaseConn(config)

    def storeInDatabase(self, p):
        with self._conn:
            cur = self._conn.cursor()

            if p.getDatabaseId() == -1:
                # insert profile
                sqlProfile = "INSERT INTO profile (revision, testcase) VALUES ('%s', '%s')" \
                    % (p.revision, p.testCase)
                cur.execute(sqlProfile)
                p.databaseId = cur.lastrowid

            # insert ranges
            for st in p.ranges.itervalues():
                if st.getDatabaseId() == -1:
                    sqlStacktrace = "INSERT INTO stacktrace (stacktrace) VALUES ('%s')" % (st.stacktrace)
                    cur.execute(sqlStacktrace)
                    st.databaseId = cur.lastrowid

                sqlRange = "INSERT OR REPLACE INTO range (stacktrace_id, \
                    min_value, max_value, profile_id, type_id) VALUES (%d, %.2f, %.2f, %d, %d) " \
                    % (st.databaseId, st.minValue, st.maxValue, p.databaseId, Type.BYTESWRITTEN)
                cur.execute(sqlRange)

            self._conn.commit()

    def loadFromDatabase(self, rev, tc):
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT id FROM profile WHERE revision = '%s' AND testcase = '%s'" % (rev, tc)
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                return -1  # "profile does not exist"

            p = Profile(rev, tc, self._config)
            p.databaseId = rows[0]['id']

            sql = "select * from range JOIN stacktrace ON stacktrace.id = range.stacktrace_id where profile_id = '%d'" \
                % p.databaseId
            cur.execute(sql)
            rows = cur.fetchall()
            for r in rows:
                st = r['stacktrace']
                min_value = round(r['min_value'], 2)
                max_value = round(r['max_value'], 2)
                dbId = r['id']

                stRange = MonitoredStacktraceRange(st, self._config)
                stRange.addToRange(min_value)
                stRange.addToRange(max_value)
                stRange.databaseId = dbId
                p.addRange(stRange)

            return p


class MonitoredStacktrace(object):
    '''
    classdocs
    '''

    def __init__(self, st, raw, perc, config, dbConn=None, avg_value=0):
        '''
        Constructor
        '''
        self.stacktrace = st
        self.rawBytes = raw
        self.percentage = perc
        self.databaseId = -1
        self.avgValue = avg_value

        self._config = config
        if dbConn == None:
            self._conn = getDatabaseConn(config)
        else:
            self._conn = dbConn

    def getDatabaseId(self):
        if self.databaseId != -1:
            return self.databaseId
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT id FROM stacktrace WHERE stacktrace = '%s'" % self.stacktrace
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                return -1
            self.databaseId = rows[0]['id']
            return self.databaseId

    def __str__(self):
        return "[MonitoredStacktrace: %s, rawBytes: %d, percentage: %d, avg value: %.2f]" \
            % (self.stacktrace, self.rawBytes, self.percentage, self.avg_value)


class MonitoredStacktraceRange(object):
    '''
    classdocs
    '''

    def __init__(self, st, config, dbConn=None):
        '''
        Constructor
        '''
        self.stacktrace = st
        self.minValue = None
        self.maxValue = None
        self.databaseId = -1
        self._config = config
        if dbConn == None:
            self._conn = getDatabaseConn(config)
        else:
            self._conn = dbConn

    def addToRange(self, i):
        '''
        Add i to the range, extend the range if necessary.
        '''
        if (self.minValue == None) or (i < self.minValue):
            self.minValue = i
        if (self.maxValue == None) or (i > self.maxValue):
            self.maxValue = i

    def isInRange(self, value):
        return value >= self.minValue and value <= self.maxValue

    def getBytesOff(self, value):
        '''
        Returns the number of bytes value is outside this range.
        '''
        if value > self.maxValue:
            return value - self.maxValue
        elif value < self.minValue:
            # TODO check if this makes sense... or should we use minValue - value?
            return value - self.minValue
        else:
            return 0

    def __str__(self):
        return "[MonitoredStacktraceRange: (min: %.2f, max: %.2f) %s]" % (self.minValue, self.maxValue, self.stacktrace)

    def getDatabaseId(self):
        if self.databaseId != -1:
            return self.databaseId

        with self._conn:
            cur = self._conn.cursor()
            sqlCheck = "SELECT id FROM stacktrace WHERE stacktrace = '%s'" % self.stacktrace
            cur.execute(sqlCheck)
            rows = cur.fetchall()
            if len(rows) == 1:
                self.databaseId = rows[0][0]
                return rows[0][0]
            else:
                return -1


class MonitoredSession(object):
    '''
    classdocs
    '''
    def __init__(self, rev, tc, config, isTestRun=0, totalActions=0, totalBytes=0):
        '''
        Constructor
        '''
        self.revision = rev
        self.testCase = tc
        self.stacktraces = {}
        self.databaseId = -1
        self.isTestRun = isTestRun

        self._config = config
        self.totalActions = totalActions
        self.totalBytes = totalBytes
        # self.lookupDict = {}
        # if filename != "":
        #    self.loadSession()

    def __str__(self):
        result = "[MonitoredSession: revision %s, test case %s " % (self.revision, self.testCase)
        for st in self.stacktraces:
            result += "%s\n" % st
        return "%s]" % result

    def addStacktrace(self, st):
        self.stacktraces[st.stacktrace] = st


'''
    unused, didn't make sense :)
    def compareSessions(self, s2):
        # get union of session entries and initialize to 0
        # note: we do not take thread id into account at the moment!!
        compared = {}
        print "size self: " + str(len(self.stacktraces))
        for st in self.stacktraces:
            compared[st.stacktrace] = {}
            compared[st.stacktrace]['s1'] = st.rawBytes

        print "size compared after s1: " + str(len(compared))

        for st in s2.stacktraces:
            if not st.stacktrace in compared:
                compared[st.stacktrace] = {}
            compared[st.stacktrace]['s2'] = st.rawBytes

        for st in compared:
            if not 's1' in  compared[st]:
                compared[st]['s1'] = 0
            if not 's2' in  compared[st]:
                compared[st]['s2'] = 0

        print "size compared after s2: " + str(len(compared))
        # print str(compared)
        # calculate difference
        for st in compared:
            diff = compared[st]['s2'] - compared[st]['s1']
            print str(diff) + " (" + st + ")"
'''


class SessionHelper(object):
    def __init__(self, config):
        self._config = config
        self._conn = getDatabaseConn(config)

    def getAllRevisions(self, testcase):
        sql = "SELECT DISTINCT(revision) FROM run"
        with self._conn:
            cur = self._conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            revisions = []
            if len(rows) == 0:
                print "No revisions found for testcase '%s'" % testcase
                sys.exit(0)
            for r in rows:
                revisions.append(r['revision'])
            return revisions

    def loadSessionFromCSV(self, rev, tc, filename="", isTestRun=0):
        assert filename != "", "Filename not set for session"
        s = MonitoredSession(rev, tc, isTestRun)
        # read CSV
        with open(filename, 'rb') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for line in reader:
                st = line['TRACE'].strip()
                b = Decimal(line['BYTES'])
                count = Decimal(line['COUNT'])
                avgValue = round(b / count, 2)
                # perc = Decimal(line['PERC'])
                # note: perc is unused at the moment
                record = MonitoredStacktrace(st, b, 0, self._config, avg_value=avgValue)
                s.stacktraces[st] = record

        return s

    def appendData(self, sess, filename):
        with open(filename, 'rb') as csvfile:
            reader = csvfile.readlines()
            totalActions = reader[2].split(':')[1].strip()
            totalBytes = reader[3].split(':')[1].strip()
            sess.totalActions = totalActions
            sess.totalBytes = totalBytes

    def storeInDatabase(self, s):
        '''
        Sessions are immutable, so only store in the database if it
        does not have a databaseId yet.
        '''
        with self._conn:
            cur = self._conn.cursor()

            if s.databaseId == -1:
                # insert profile
                sqlProfile = "INSERT OR REPLACE INTO run (revision, testcase, is_test_run, total_actions, " \
                        " total_bytes) VALUES ('%s', '%s', '%s', '%s', '%s')" \
                         % (s.revision, s.testCase, s.isTestRun, s.totalActions, s.totalBytes)
                cur.execute(sqlProfile)
                s.databaseId = cur.lastrowid

            # insert ranges
            for st in s.stacktraces.itervalues():
                if st.getDatabaseId() == -1:
                    sqlStacktrace = "INSERT INTO stacktrace (stacktrace) VALUES ('%s')" % (st.stacktrace)
                    cur.execute(sqlStacktrace)
                    st.databaseId = cur.lastrowid
                sqlRange = "INSERT OR REPLACE INTO monitored_value (stacktrace_id, run_id, type_id, value, avg_value) \
                    VALUES (%d, %d, %d, %d, %.2f) "  \
                    % (st.getDatabaseId(), s.databaseId, Type.BYTESWRITTEN, st.rawBytes, st.avgValue)
                cur.execute(sqlRange)

            self._conn.commit()

    def loadFromDatabase(self, rev, tc):
        '''
        Note: returns array of MonitoredSession objects, because we may have multiple sessions
        for the same revision and test case (in contrast to a profile, of which we have only one.
        '''
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT id, is_test_run FROM run WHERE revision = '%s' AND testcase = '%s'" % (rev, tc)
            cur.execute(sql)
            rows = cur.fetchall()
            assert len(rows) > 0, "run does not exist"
            sessions = []
            for r1 in rows:

                m = MonitoredSession(rev, tc, self._config, r1['is_test_run'])
                m.databaseId = r1['id']

                sql = "select * from monitored_value JOIN stacktrace ON stacktrace.id = monitored_value.stacktrace_id \
                    where run_id = '%d'" % m.databaseId
                cur.execute(sql)
                rows = cur.fetchall()
                for r2 in rows:
                    st = r2['stacktrace']
                    value = r2['value']
                    dbId = r2['id']
                    avgValue = round(r2['avg_value'], 2)
                    s = MonitoredStacktrace(st, value, 0, self._config, self._conn, avgValue)
                    s.databaseId = dbId
                    m.stacktraces[st] = s

                sessions.append(m)

            return sessions

    def storeMetricInDatabase(self, s, m):
        assert s.databaseId != -1, "please store session in database first"
        with self._conn:
            cur = self._conn.cursor()
            sql = "INSERT INTO metric_value (run_id, metric_type_id, value, profile_id) VALUES \
                    (%d, %d, %f, %d)" % (s.databaseId, m.typeId, m.value, m.profileId)
            cur.execute(sql)


class MetricValue(object):
    def __init__(self, typeId, value, profileId, runs=1, bytesOff=0, rangeDiff=0, totalImpact=0):
        self.typeId = typeId
        self.value = value
        self.profileId = profileId
        self.runs = runs
        self.bytesOff = bytesOff
        self.rangeDiff = rangeDiff
        self.totalImpact = totalImpact

    def __str__(self):
        return "[MetricValue: %.2f, %d (%d) off: %.2f / %.2f]" \
            % (self.value, self.typeId, self.runs, self.bytesOff, self.rangeDiff)

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value


class ActivityMatrix(object):
    def __init__(self, profileId, runs, typeId, revision, testcase):
        self.matrix = {}
        self.metrics = {}
        self.databaseId = -1
        self.profileId = profileId
        self.runs = runs
        self.typeId = typeId
        self.revision = revision
        self.testcase = testcase
        self.sortedMetrics = {}

    def addFitsVector(self, v):
        for st in v:
            if not st in self.matrix:
                self.matrix[st] = []
            self.matrix[st].append(v[st])
        # print self.matrix

    def calcSimilarity(self):
        '''
        Returns the (simplified) cosine similarity for fit vector v
        and a vector with the same total number of items, all initialized
        to 1's.

        The rationale behind this is that we want to see how different the
        fit vector is compared to the profile (which is the fit vector with
        all 1's).

        A similarity of 1 means all elements are equal, hence all elements
        of the new vector fit in the ranges defined in the profile.

        A similarity of 0 means all elements are different, hence no elements
        fit in the defined ranges.

        A value between 0 and 1 means the vectors are partly different.
        '''
        self.metrics[MetricType.COSINESIM] = {}
        for st in self.matrix:
            avgBytesOff = 0
            avgRangeDiff = 0
            v = self.matrix[st]
            d1 = sqrt(len(v))
            ones = 0
            for i in v:
                ones += i['fits']
                # doesn't really belong here but store this in the metric to give extra info
                avgBytesOff = avgBytesOff + i['bytesOff']
                avgRangeDiff = avgRangeDiff + i['rangeDiff']
            if ones == 0:
                sim = 0
            else:
                d2 = sqrt(ones)
                sim = ones / (d1 * d2)
            metricValue = MetricValue(MetricType.COSINESIM, sim, -1, len(v), avgBytesOff / len(v), avgRangeDiff / len(v))
            self.metrics[MetricType.COSINESIM][st] = metricValue

    def printMatrix(self):
        for t in self.metrics:
            sorted_metrics = sorted(self.metrics[t].iteritems(), key=operator.itemgetter(1))
            print "Type: %d" % t
            for st in sorted_metrics:
                print "%s - %s" % (st[1], st[0])


class MatrixHelper(object):

    def __init__(self, config):
        self._config = config
        self._conn = getDatabaseConn(config)

    def getPreviousRevision(self, rev=-1):
        with self._conn:
            cur = self._conn.cursor()
            if rev == -1:
                sql = "SELECT revision FROM git_log ORDER BY id DESC LIMIT 1"
            else:
                sql = "SELECT revision FROM git_log WHERE id < (SELECT id FROM git_log WHERE revision = '%s') " \
                 " ORDER BY id DESC" % rev
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                return -1
            return rows[0]['revision']

    def getStacktraceId(self, st):
        with self._conn:
            cur = self._conn.cursor()

            sql = "SELECT id FROM stacktrace WHERE stacktrace = '%s'" % st
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                return -1
            return rows[0]['id']

    def storeInDatabase(self, m):
        with self._conn:
            cur = self._conn.cursor()
            if m.databaseId == -1:
                # insert profile
                sql = "INSERT INTO activity_matrix (revision, testcase, checked_profile, runs, type_id) \
                            VALUES ('%s', '%s', '%d', '%d', '%d')" \
                            % (m.revision, m.testcase, m.profileId, m.runs, m.typeId)
                cur.execute(sql)
                m.databaseId = cur.lastrowid
            # insert ranges
            for t in m.metrics:
                for mt in m.metrics[t].iteritems():
                    st = mt[0]
                    stacktraceId = self.getStacktraceId(st)
                    if stacktraceId == -1:
                        sql = "INSERT INTO stacktrace (stacktrace) VALUES ('%s')" % (mt[0])
                        cur.execute(sql)
                        stacktraceId = cur.lastrowid
                    metric = mt[1]

                    # add the number of calls to the activity_metric for easier querying
                    sqlCalls = "SELECT avg(value/avg_value) as v, stacktrace_id FROM monitored_value  \
                               JOIN run ON monitored_value.run_id = run.id WHERE revision = '%s' \
                               AND stacktrace_id = '%d'" % (m.revision, stacktraceId)
                    cur.execute(sqlCalls)
                    rows = cur.fetchall()
                    if len(rows) == 0:
                        calls = 0
                    else:
                        calls = rows[0]['v']

                    sqlRange = "INSERT INTO activity_metric (matrix_id, value, runs, stacktrace_id, type_id, \
                        bytes_off, range_diff, calls) VALUES (%d, %.2f, %d, %d, %d, %.2f, %.2f, %d) " \
                        % (m.databaseId, metric.value, metric.runs, stacktraceId, metric.typeId, metric.bytesOff,
                           metric.rangeDiff, round(calls))

                    cur.execute(sqlRange)
            self._conn.commit()

    def getMetricPerStacktrace(self, typeId):
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT value, stacktrace, matrix_id FROM activity_metric " \
                " JOIN stacktrace ON stacktrace_id = stacktrace.id " \
                " WHERE stacktrace_id = 1 AND type_id = '%d' ORDER BY matrix_id" % typeId
            cur.execute(sql)
            rows = cur.fetchall()
            return rows

    def getAvgMetricPerRevision(self, typeId):
        with self._conn:
            cur = self._conn.cursor()
            sql = "select revision, profile_id,  avg(value) as value from metric_value " \
                " JOIN profile ON profile_id = profile.id WHERE metric_type_id = '%d' " \
                " GROUP BY profile_id" % typeId
            cur.execute(sql)
            rows = cur.fetchall()
            return rows

    def getTotalBytesWrittenPerRevision(self):
        with self._conn:
            cur = self._conn.cursor()
            sql = "SELECT profile.id as profile_id, AVG(total_bytes) as value, run.revision as rev FROM run " \
                    " JOIN profile ON profile.revision = run.revision " \
                    " JOIN git_log on run.revision = git_log.revision " \
                    " WHERE is_test_run = 1 GROUP BY run.revision ORDER BY git_log.id"

            cur.execute(sql)
            rows = cur.fetchall()
            return rows

    def getCallsPerStacktrace(self, rev):
        with self._conn:
            cur = self._conn.cursor()
            sql = "select value/avg_value as v, stacktrace_id, stacktrace FROM monitored_value " \
                " JOIN run ON run_id = run.id JOIN stacktrace ON stacktrace.id = stacktrace_id " \
                " WHERE revision = '%s' AND is_test_run = 1 ORDER BY stacktrace_id, run_id " % rev
            # print sql
            cur.execute(sql)
            rows = cur.fetchall()
            result = {}
            for r in rows:
                if r['stacktrace'] not in result.keys():
                    result[r['stacktrace']] = []
                result[r['stacktrace']].append(r['v'])
            return result

    def loadFromDatabase(self, revision, typeId):
        with self._conn:
            # load matrix
            cur = self._conn.cursor()
            sql = "SELECT id, revision, testcase, checked_profile, runs, type_id FROM activity_matrix " \
                    "WHERE revision = '%s' AND type_id = '%d'" % (revision, typeId)
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                print "No matrix found for revision %s and type %d" % (revision, typeId)
                return None
            r = rows[0]
            m = ActivityMatrix(r['checked_profile'], r['runs'], typeId, revision, r['testcase'])
            m.databaseId = r['id']

            # load metrics
            sql = "SELECT bytes_off*calls as total, value, stacktrace, runs, bytes_off, range_diff, stacktrace \
                    FROM activity_metric JOIN stacktrace ON stacktrace_id = stacktrace.id WHERE matrix_id = '%d' \
                    ORDER BY value, total DESC, calls DESC, abs(bytes_off) DESC " % m.databaseId
            cur.execute(sql)
            rows = cur.fetchall()
            m.metrics[typeId] = {}
            m.sortedMetrics[typeId] = []
            for r in rows:
                v = MetricValue(typeId, r['value'], m.profileId, r['runs'], round(r['bytes_off']), r['range_diff'],
                                    round(r['total']))
                m.metrics[typeId][r['stacktrace']] = v
                m.sortedMetrics[typeId].append([r['stacktrace'], v])

            sorted_metrics = sorted(m.metrics[typeId].iteritems(), key=operator.itemgetter(1))
            m.metrics[typeId] = sorted_metrics
            # m.printMatrix()
            return m


# enums for different types of data monitored, note: for now only 1 type exists
def enum(**enums):
    return type('Enum', (), enums)

Type = enum(BYTESWRITTEN=1)
MetricType = enum(COSINESIM=1, OCHIAI=2)
