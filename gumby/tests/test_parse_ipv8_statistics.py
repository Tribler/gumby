import os
import shutil
import tempfile
import unittest

from experiments.ipv8.parse_ipv8_statistics import IPv8StatisticsParser


class TestIPv8StatisticsParser(unittest.TestCase):

    TESTS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    TESTS_DATA_DIR = os.path.abspath(os.path.join(TESTS_DIR, u"data"))

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_aggregate_messages(self):
        """
        Test aggregating IPv8 message statistics
        """
        stats_parser = IPv8StatisticsParser(self.test_dir)

        # Setup a localhost-like file tree
        os.mkdir(os.path.join(self.test_dir, "1"))
        os.mkdir(os.path.join(self.test_dir, "2"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats1.txt"),
                    os.path.join(self.test_dir, "1", "ipv8_statistics.txt"))
        shutil.copy(os.path.join(self.TESTS_DATA_DIR, "stats2.txt"),
                    os.path.join(self.test_dir, "2", "ipv8_statistics.txt"))

        stats_parser.aggregate_messages()
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "ipv8_msg_stats.csv")))
