#!/usr/bin/env python3
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
from asyncio import ensure_future, get_event_loop, sleep

from gumby.instrumentation import init_instrumentation

from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.session import Session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


class IdleTribleRunner():

    def __init__(self):
        init_instrumentation()
        self.session = None

    async def run(self):
        config = TriblerConfig()
        config.set_state_dir(os.path.abspath(os.path.join(BASE_DIR, "output", "tribler-state")),)
        config.set_http_api_enabled(False)
        config.set_ipv8_port(21000)
        config.set_libtorrent_port(21005)

        self.session = Session(config)
        try:
            await self.session.start()
        except Exception as e:
            print(str(e))
            get_event_loop().stop()
        else:
            print("Tribler started")

        if "TRIBLER_EXECUTION_TIME" in os.environ:
            run_time = int(os.environ["TRIBLER_EXECUTION_TIME"])
        else:
            run_time = 60 * 10  # Run for 10 minutes by default

        await sleep(run_time)

        print("Stopping Tribler idle run")
        await self.session.shutdown()
        get_event_loop().stop()


if __name__ == "__main__":
    runner = IdleTribleRunner()
    ensure_future(runner.run())
    get_event_loop().run_forever()
    get_event_loop().close()

#
# tribler_idle_run.py ends here
