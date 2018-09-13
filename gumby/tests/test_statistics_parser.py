import os
import shutil
import tempfile
import unittest

from gumby.statsparser import StatisticsParser


class TestStatisticsParser(unittest.TestCase):

    TESTS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    TESTS_DATA_DIR = os.path.abspath(os.path.join(TESTS_DIR, u"data"))

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_yield_files_das5(self):
        """
        Test the yield_files method with a DAS5 structure
        """
        stats_parser = StatisticsParser(self.test_dir)

        # Setup a DAS5-like file structure
        os.mkdir(os.path.join(self.test_dir, "localhost"))
        os.mkdir(os.path.join(self.test_dir, "localhost", "node030"))
        os.mkdir(os.path.join(self.test_dir, "localhost", "node031"))
        os.mkdir(os.path.join(self.test_dir, "localhost", "node030", "1"))
        os.mkdir(os.path.join(self.test_dir, "localhost", "node031", "1"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats1.txt"),
                    os.path.join(self.test_dir, "localhost", "node030", "1", "stats.txt"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats2.txt"),
                    os.path.join(self.test_dir, "localhost", "node031", "1", "stats.txt"))

        items = stats_parser.yield_files('stats.txt')
        self.assertEqual(len(list(items)), 2)

    def test_yield_files_localhost(self):
        """
        Test the yield_files method with a localhost structure
        """
        stats_parser = StatisticsParser(self.test_dir)

        # Setup a localhost-like file structure
        os.mkdir(os.path.join(self.test_dir, "1"))
        os.mkdir(os.path.join(self.test_dir, "2"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats1.txt"), os.path.join(self.test_dir, "1", "stats.txt"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats2.txt"), os.path.join(self.test_dir, "2", "stats.txt"))

        items = stats_parser.yield_files('stats.txt')
        self.assertEqual(len(list(items)), 2)
