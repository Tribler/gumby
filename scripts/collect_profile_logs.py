#!/usr/bin/env python2
import os
import shutil
import sys

from gumby.statsparser import StatisticsParser


class ProfileCollector(StatisticsParser):
    """
    This class is responsible for collecting profile logs and placing them in one directory.
    """

    def run(self):
        if not os.path.exists('profile'):
            os.mkdir('profile')

        for peer_nr, filename, dir in self.yield_files('yappi.stats'):
            shutil.copyfile(filename, os.path.join("profile", "%s.stats" % peer_nr))

# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

collector = ProfileCollector(sys.argv[1])
collector.run()
