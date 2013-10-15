'''
Created on Jul 4, 2013

@author: corpaul
'''
import unittest
from gumby.settings import loadConfig
from gumby.spectraperf.performanceprofile import *
from gumby.spectraperf.databasehelper import *

DATABASE = "performance_test.db"
config = loadConfig("test.conf")


class TestPerformanceFunctions(unittest.TestCase):

    def testAddToRange(self):
        s = MonitoredStacktrace("test", 10, 25, config, avg_value=10)

        sess = MonitoredSession("rev1", "test_batch", config)
        sess.addStacktrace(s)

        p = Profile("rev1", "test_batch", config)
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
        st1 = MonitoredStacktrace("test", 10, 25, config, avg_value=10)
        st2 = MonitoredStacktrace("test", 20, 25, config, avg_value=20)

        sess1 = MonitoredSession("rev1", "test_batch", config)
        sess1.addStacktrace(st1)
        sess2 = MonitoredSession("rev1", "test_batch", config)
        sess2.addStacktrace(st2)

        p = Profile("rev1", "test_batch", config)
        p.addSession(sess1)
        p.addSession(sess2)

        self.assertTrue(p.getRange(st1.stacktrace) == p.getRange(st2.stacktrace))

        self.assertTrue(p.getRange(st1.stacktrace).isInRange(15))
        self.assertTrue(p.getRange(st1.stacktrace).isInRange(10))
        self.assertFalse(p.getRange(st1.stacktrace).isInRange(9))
        self.assertFalse(p.getRange(st1.stacktrace).isInRange(21))

    def testFitsProfile(self):
        s1 = MonitoredStacktrace("test1", 10, 25, config, avg_value=10)
        s2 = MonitoredStacktrace("test2", 25, 25, config, avg_value=25)

        sess1 = MonitoredSession("rev1", "test_batch", config)
        sess1.addStacktrace(s1)

        p = Profile("rev1", "test_batch", config)
        p.addToRange("test1", 10)
        p.addToRange("test1", 20)

        fits = p.fitsProfile(sess1)
        self.assertEqual(fits["test1"]["fits"], 1)

        sess1.addStacktrace(s2)
        # should raise AssertionError because we did not add a range for test2 yet
        # with self.assertRaises(AssertionError):
        #     fits = p.fitsProfile(sess1)

        p.addToRange("test2", 10)
        p.addToRange("test2", 20)
        fits = p.fitsProfile(sess1)

        self.assertEqual(fits["test1"]["fits"], 1)
        self.assertEqual(fits["test2"]["fits"], 0)

        p2 = Profile("rev1", "test_batch", config)
        p2.addToRange("test2", 10)
        p2.addToRange("test2", 20)
        sess2 = MonitoredSession("rev1", "test_batch", config)
        sess2.addStacktrace(s2)
        fits = p2.fitsProfile(sess2)
        self.assertEqual(fits["test2"]["fits"], 0)

    def testSimilarity(self):
        v1 = {"st1": {'fits': 1}, "test2": {'fits': 1}, "test3": {'fits': 1}, "test4": {'fits': 1},
              "test5": {'fits': 0}}
        v2 = {"st1": {'fits': 1}, "test2": {'fits': 1}, "test3": {'fits': 1}, "test4": {'fits': 1},
              "test5": {'fits': 1}}
        p = Profile("24435a", "test_batch", config)
        self.assertAlmostEqual(p.similarity(v2).value, 1)
        self.assertAlmostEqual(p.similarity(v1).value, 0.894427191)

    def testProfileHelper(self):
        # reset database before testing
        # InitDatabase(config)

        s1 = MonitoredStacktrace("test1", 10, 25, config, avg_value=10)
        s2 = MonitoredStacktrace("test2", 25, 25, config, avg_value=25)

        sess1 = MonitoredSession("rev1", "test_batch", config)
        sess1.addStacktrace(s1)
        sess1.addStacktrace(s2)

        p = Profile("rev1", "test_batch", config)

        # add a max value for the range
        p.addToRange("test1", 10)
        p.addToRange("test1", 20)
        p.addToRange("test2", 10)
        p.addToRange("test2", 20)

        h = ProfileHelper(config)

        # empty profile should have an id
        self.assertNotEqual(p.getDatabaseId(), -1)
        # print p
        h.storeInDatabase(p)

        self.assertNotEqual(p.getDatabaseId(), -1)

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
        helper = SessionHelper(config)
        sess1 = helper.loadSessionFromCSV("rev1", "test_batch", "data/test_session1.csv")
        sess2 = helper.loadSessionFromCSV("rev1", "test_batch", "data/test_session2.csv")
        # print sess1
        # print sess2

        p = Profile("rev1", "test_batch", config)
        p.addSession(sess1)
        p.addSession(sess2)
        # print p
        self.assertTrue(p.getRange("test1").isInRange(15))
        self.assertTrue(p.getRange("test1").isInRange(10))
        self.assertFalse(p.getRange("test1").isInRange(9))
        self.assertFalse(p.getRange("test1").isInRange(21))

        helper.storeInDatabase(sess1)
        helper.storeInDatabase(sess2)

        revs = helper.getAllRevisions("test_batch")
        self.assertEqual(len(revs), 1)

        sess3 = helper.loadFromDatabase("rev1", "test_batch")
        self.assertEqual(len(sess3), 2)
        for s in sess3:
            self.assertEqual(s.isTestRun, 0)

        sess1 = MonitoredSession("rev2", "test_batch", config, 1)
        helper.storeInDatabase(sess1)
        revs = helper.getAllRevisions("test_batch")
        self.assertEqual(len(revs), 2)
        sess3 = helper.loadFromDatabase("rev2", "test_batch")
        self.assertEqual(len(sess3), 1)
        for s in sess3:
            self.assertEqual(s.isTestRun, 1)

        # TODO: verify this in some way, for now just see it doesnt throw
        # sql errors
        sess1 = helper.loadSessionFromCSV("rev1", "test_batch", "data/test_session1.csv")
        fits = p.fitsProfile(sess1)
        metricValue = p.similarity(fits)
        helper.storeInDatabase(sess1)
        helper.storeMetricInDatabase(sess1, metricValue)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
