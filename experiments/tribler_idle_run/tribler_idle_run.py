#!/usr/bin/env python
# tribler_idle_run.py ---
#
# Filename: test_30m_run.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Jul 15 15:05:16 2013 (+0200)

# Commentary:
#
#
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

import unittest

import sys
import os

from gumby.instrumentation import init_instrumentation

os.chdir(os.path.abspath('./tribler'))
sys.path.append('.')

from Tribler.Test.test_as_server import TestGuiAsServer

class TestGuiGeneral(TestGuiAsServer):

    def test_debugpanel(self):
        def end():
            self.quit()

        def do_page():
            init_instrumentation()
            if "TRIBLER_EXECUTION_TIME" in os.environ:
                run_time = int(os.environ["TRIBLER_EXECUTION_TIME"])
            else:
                run_time = 60*10 # Run for 10 minutes by default
            self.Call(run_time, end)

        self.startTest(do_page)

if __name__ == "__main__":
    unittest.main()

#
# tribler_idle_run.py ends here
