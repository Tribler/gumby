# instrumentation.py ---
#
# Filename: instrumentation.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Jul  3 17:54:21 2014 (+0200)

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
from os import environ, makedirs, path, getpid
from time import time

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python.log import msg
from twisted.conch import manhole_tap

# @CONF_OPTION PROFILE_MEMORY: Enable memory profiling for the python processes that call instrumentation.init_instrumentation() (default: false)
PROFILE_MEMORY = environ.get("PROFILE_MEMORY", "FALSE").upper() == "TRUE"
# @CONF_OPTION PROFILE_MEMORY_INTERVAL: Memory dump interval. (default: 60)
PROFILE_MEMORY_INTERVAL = float(environ.get("PROFILE_MEMORY_INTERVAL", 60))
# @CONF_OPTION PROFILE_MEMORY_PID_MODULO: Only start the memory dumper for (aproximately) one out of N processes. (default: all processes)
PROFILE_MEMORY_PID_MODULO = int(environ.get("PROFILE_MEMORY_PID_MODULO", 0))

# @CONF_OPTION MANHOLE_ENABLE: Enable manhole (telnet access to the python processes), for debugging purposes. User: gumby, pass is empty (default: false)
MANHOLE_ENABLE = environ.get("MANHOLE_ENABLE", "FALSE").upper() == "FALSE"
# @CONF_OPTION MANHOLE_PORTL Port that manhole should listen to. (default: 2323)
MANHOLE_PORT = int(environ.get("MANHOLE_PORT", 2323))

manhole = None
manhole_namespace = {}

PID = getpid()


def init_instrumentation():
    """
    Instrumentation initializer, starts the components enabled trough config options
    """
    if PROFILE_MEMORY and PROFILE_MEMORY_PID_MODULO and (PID % PROFILE_MEMORY_PID_MODULO == 0):
        start_memory_dumper()

    if MANHOLE_ENABLE:
        start_manhole()


def start_memory_dumper():
    """
    Initiates the memory profiler.
    """
    msg("starting memory dump looping call")
    from meliae import scanner
    start = time()
    meliae_out_dir = path.join(environ["OUTPUT_DIR"], "meliae", str(PID))
    makedirs(meliae_out_dir)
    meliae_out_file = path.join(meliae_out_dir, "memory-%s.out")
    LoopingCall(lambda: scanner.dump_all_objects(meliae_out_file % str(time() - start))).start(PROFILE_MEMORY_INTERVAL,
                                                                                               now=True)
    reactor.addSystemEventTrigger("before", "shutdown",
                                  lambda: scanner.dump_all_objects(meliae_out_file % str(time() - start) + "-shutdown"))


def start_manhole():
    """
    Starts a manhole telnet server listening on MANHOLE_PORT
    """
    passwd_path = os.path.join(environ['PROJECT_DIR'], 'lib', 'passwd')
    global manhole
    manhole = manhole_tap.makeService({
        'namespace': manhole_namespace,
        'telnetPort': 'tcp:%d:interface:127.0.0.1' % MANHOLE_PORT,
        'sshPort': None,
        'passwd': passwd_path,
    })


#
# instrumentation.py ends here
