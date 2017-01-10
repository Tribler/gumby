#!/usr/bin/env python2
# tribler_idle_run.py ---
#
# Filename: tribler_idle_run.py
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
# 19th of May 2016: Now uses the Twistd tribler plugin to start Tribler.
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

import sys
import os
from twisted.internet import reactor

from gumby.instrumentation import init_instrumentation


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

sys.path.append(os.path.abspath('./tribler'))
sys.path.append(os.path.abspath('./tribler/twisted/plugins'))

from tribler_plugin import TriblerServiceMaker


class IdleTribleRunner():

    def __init__(self):
        init_instrumentation()
        self.service = None

    def start(self):
        self.service = TriblerServiceMaker()

        if "TRIBLER_EXECUTION_TIME" in os.environ:
            run_time = int(os.environ["TRIBLER_EXECUTION_TIME"])
        else:
            run_time = 60*10  # Run for 10 minutes by default

        auto_join_channels = os.environ.get("AUTO_JOIN_CHANNELS", "FALSE").upper() == "TRUE"

        reactor.callLater(run_time, self.stop)
        self.service.start_tribler({'restapi': 0, 'dispersy': 21000,
                                    'statedir': os.path.abspath(os.path.join(BASE_DIR, "output", "tribler-state")),
                                    'libtorrent': 21005, 'auto-join-channel': True if auto_join_channels else None})

    def stop(self):
        # TODO(Laurens): Current the plugin does not offer a function to shutdown it nicely
        # so once this is added, make sure it is not violently killed.
        self.service.shutdown_process("Stopping Tribler idle run", code=0)

if __name__ == "__main__":
    runner = IdleTribleRunner()
    reactor.callWhenRunning(runner.start)
    reactor.run()

#
# tribler_idle_run.py ends here
