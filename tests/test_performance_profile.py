'''
Created on Jul 4, 2013

@author: corpaul
'''
import unittest
from spectraperf.performanceprofile import *
from spectraperf.databasehelper import *

DATABASE = "performance_test.db"


class TestPerformanceFunctions(unittest.TestCase):

    def testAddToRange(self):
        s = MonitoredStacktrace("test", 10, 25)

        sess = MonitoredSession("rev1", "test_batch")
        sess.addStacktrace(s)

        p = Profile("rev1", "test_batch")
        p.addSession(sess)

        self.assertEqual(p.getRange("test").minValue, 10)
        self.assertEqual(p.getRange("test").maxValue, 10)

        p.addToRange("test", 20)
        self.assertEqual(p.getRange("test").minValue, 10)
        self.assertEqual(p.getRange("test").maxValue, 20)

        p.addToRange("test", 5)
        self.assertEqual(p.getRange("test").minValue, 5)
        self.assertEqual(p.getRange("test").maxValue, 20)

        p.addToRange("test", 15)
        self.assertEqual(p.getRange("test").minValue, 5)
        self.assertEqual(p.getRange("test").maxValue, 20)

    def testIsInRange(self):
        st1 = MonitoredStacktrace("test", 10, 25)
        st2 = MonitoredStacktrace("test", 20, 25)

        sess1 = MonitoredSession("rev1", "test_batch")
        sess1.addStacktrace(st1)
        sess2 = MonitoredSession("rev1", "test_batch")
        sess2.addStacktrace(st2)

        p = Profile("rev1", "test_batch")
        p.addSession(sess1)
        p.addSession(sess2)

        self.assertTrue(p.getRange(st1.stacktrace) == p.getRange(st2.stacktrace))

        self.assertTrue(p.getRange(st1.stacktrace).isInRange(15))
        self.assertTrue(p.getRange(st1.stacktrace).isInRange(10))
        self.assertFalse(p.getRange(st1.stacktrace).isInRange(9))
        self.assertFalse(p.getRange(st1.stacktrace).isInRange(21))

    def testFitsProfile(self):
        s1 = MonitoredStacktrace("test1", 10, 25)
        s2 = MonitoredStacktrace("test2", 25, 25)

        sess1 = MonitoredSession("rev1", "test_batch")
        sess1.addStacktrace(s1)

        p = Profile("rev1", "test_batch")
        p.addToRange("test1", 10)
        p.addToRange("test1", 20)

        fits = p.fitsProfile(sess1)
        self.assertEqual(fits["test1"], 1)

        sess1.addStacktrace(s2)
        # should raise AssertionError because we did not add a range for test2 yet
        # with self.assertRaises(AssertionError):
        #     fits = p.fitsProfile(sess1)

        p.addToRange("test2", 10)
        p.addToRange("test2", 20)
        fits = p.fitsProfile(sess1)

        self.assertEqual(fits["test1"], 1)
        self.assertEqual(fits["test2"], 0)

        p2 = Profile("rev1", "test_batch")
        p2.addToRange("test2", 10)
        p2.addToRange("test2", 20)
        sess2 = MonitoredSession("rev1", "test_batch")
        sess2.addStacktrace(s2)
        fits = p2.fitsProfile(sess2)
        self.assertEqual(fits["test2"], 0)

    def testSimilarity(self):
        v1 = {"test1": 1, "test2": 1, "test3": 1, "test4": 1, "test5": 0}
        v2 = {"test1": 1, "test2": 1, "test3": 1, "test4": 1, "test5": 1}
        p = Profile("24435a", "test_batch")
        self.assertAlmostEqual(p.similarity(v2), 1)
        self.assertAlmostEqual(p.similarity(v1), 0.894427191)

    def testProfileHelper(self):
        # reset database before testing
        InitDatabase(DATABASE)

        s1 = MonitoredStacktrace("test1", 10, 25)
        s2 = MonitoredStacktrace("test2", 25, 25)

        sess1 = MonitoredSession("rev1", "test_batch")
        sess1.addStacktrace(s1)
        sess1.addStacktrace(s2)

        p = Profile("rev1", "test_batch", DATABASE)

        # add a max value for the range
        p.addToRange("test1", 10)
        p.addToRange("test1", 20)
        p.addToRange("test2", 10)
        p.addToRange("test2", 20)

        h = ProfileHelper(DATABASE)

        # empty profile
        self.assertEqual(h.getDatabaseId(p), -1)
        # print p
        h.storeInDatabase(p)

        self.assertNotEqual(h.getDatabaseId(p), -1)

        p.addSession(sess1)
        # print p

        h.storeInDatabase(p)

        # load p from the database

        p = h.loadFromDatabase("rev1", "test_batch")
        # print p
        self.assertTrue(p.getRange("test1").isInRange(15))
        self.assertTrue(p.getRange("test1").isInRange(10))
        self.assertFalse(p.getRange("test1").isInRange(9))
        self.assertFalse(p.getRange("test1").isInRange(21))

    def testSessionHelper(self):
        helper = SessionHelper(DATABASE)
        sess1 = helper.loadSessionFromCSV("rev1", "test_batch", "data/test_session1.csv")
        sess2 = helper.loadSessionFromCSV("rev1", "test_batch", "data/test_session2.csv")
        # print sess1
        # print sess2

        p = Profile("rev1", "test_batch")
        p.addSession(sess1)
        p.addSession(sess2)
        # print p
        self.assertTrue(p.getRange("test1").isInRange(15))
        self.assertTrue(p.getRange("test1").isInRange(10))
        self.assertFalse(p.getRange("test1").isInRange(9))
        self.assertFalse(p.getRange("test1").isInRange(21))

        helper.storeInDatabase(sess1)
        helper.storeInDatabase(sess2)

        sess3 = helper.loadFromDatabase("rev1", "test_batch")
        self.assertEqual(len(sess3), 2)
        for s in sess3:
            self.assertEqual(s.isTestRun, 0)

        sess1 = MonitoredSession("rev2", "test_batch", 1)
        helper.storeInDatabase(sess1)
        sess3 = helper.loadFromDatabase("rev2", "test_batch")
        self.assertEqual(len(sess3), 1)
        for s in sess3:
            self.assertEqual(s.isTestRun, 1)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
