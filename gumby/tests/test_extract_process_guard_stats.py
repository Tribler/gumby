import os
import shutil
import tempfile
import unittest

from gumby.process_guard_stats_parser import ResourceUsageParser


class TestExtractProcessGuardStats(unittest.TestCase):

    TESTS_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    PROCESS_GUARD_INPUT_DIR = os.path.abspath(os.path.join(TESTS_DIR, u"data", u"process_guard"))

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_resources(self):
        """
        Test parsing the process guard resources.
        """
        parser = ResourceUsageParser(self.PROCESS_GUARD_INPUT_DIR, self.test_dir)
        parser.parse_resource_files()

        self.assertEqual(len(parser.all_nodes), 2)

        file_prefixes = ["utimes", "stimes", "wchars", "rchars", "wchars_sum", "rchars_sum", "vsizes", "rsizes",
                         "writebytes", "readbytes", "writebytes_sum", "readbytes_sum", "threads"]
        for prefix in file_prefixes:
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, "%s.txt" % prefix)))
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, "%s_node.txt" % prefix)))

        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "axis_stats.txt")))
