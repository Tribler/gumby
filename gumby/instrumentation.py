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
import logging
from os import environ, getpid, makedirs, path
from time import time

from twisted.conch import manhole_tap
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.python.log import msg


# @CONF_OPTION PROFILE_MEMORY: Enable memory profiling for the python processes that call instrumentation.init_instrumentation() (default: false)
PROFILE_MEMORY = environ.get("PROFILE_MEMORY", "FALSE").upper() == "TRUE"
# @CONF_OPTION PROFILE_MEMORY_INTERVAL: Memory dump interval. (default: 60)
PROFILE_MEMORY_INTERVAL = float(environ.get("PROFILE_MEMORY_INTERVAL", 60))
# @CONF_OPTION PROFILE_MEMORY_PID_MODULO: Only start the memory dumper for (aproximately) one out of N processes. (default: all processes)
PROFILE_MEMORY_PID_MODULO = int(environ.get("PROFILE_MEMORY_PID_MODULO", 1))
# TODO(emilon): Implement this one
# @__NOT_IMPLEMENTED__CONF_OPTION PROFILE_MEMORY_LOG_MOST_COMMON: Do an objgraph backref chain graph for the top N most common types.
#PROFILE_MEMORY_LOG_MOST_COMMON =  int(environ.get("PROFILE_MEMORY_LOG_MOST_COMMON", 0))
# @CONF_OPTION PROFILE_MEMORY_GRAPH_BACKREF_TYPES: Space separated list of object types to generate a backref graph from (default: nothing)
PROFILE_MEMORY_GRAPH_BACKREF_TYPES = environ.get("PROFILE_MEMORY_GRAPH_BACKREF_TYPES", "")
# @CONF_OPTION PROFILE_MEMORY_GRAPH_BACKREF_AMOUNT: Amount of randomly selected objects to graph (default: 1)
PROFILE_MEMORY_GRAPH_BACKREF_AMOUNT =  int(environ.get("PROFILE_MEMORY_GRAPH_BACKREF_AMOUNT", 1))

# @CONF_OPTION MANHOLE_ENABLE: Enable manhole (telnet access to the python processes), for debugging purposes. User: gumby, pass is empty (default: false)
MANHOLE_ENABLE = environ.get("MANHOLE_ENABLE", "FALSE").upper() == "FALSE"
# @CONF_OPTION MANHOLE_PORTL Port that manhole should listen to. (default: 2323)
MANHOLE_PORT = int(environ.get("MANHOLE_PORT", 2323))

manhole = None
manhole_namespace = {}

PID = getpid()

logger = logging.getLogger()

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
    logger.info("starting memory dump looping call")
    from meliae import scanner
    # Setup the whole thing
    start = time()
    memdump_dir = path.join(environ["OUTPUT_DIR"], "memprof", str(PID))
    makedirs(memdump_dir)
    meliae_out_file = path.join(memdump_dir, "memory-%06.2f.out")
    objgraph_out_file = path.join(memdump_dir, "objgraph-%s-%06.2f-%d.png")
    if PROFILE_MEMORY_GRAPH_BACKREF_TYPES:
        import objgraph
        import random
        types = PROFILE_MEMORY_GRAPH_BACKREF_TYPES.split()

    def dump_memory():
        now = time() - start
        if PROFILE_MEMORY_GRAPH_BACKREF_TYPES:
            for type_ in types:
                for sample_number in xrange(PROFILE_MEMORY_GRAPH_BACKREF_AMOUNT):
                    objects = objgraph.by_type(type_)
                    if objects:
                        objgraph.show_chain(
                            objgraph.find_backref_chain(
                                random.choice(objects),
                                objgraph.is_proper_module),
                            filename=objgraph_out_file % (type_, now, sample_number))
                    else:
                        logger.error("No objects of type %s found!", type_)

        scanner.dump_all_objects(meliae_out_file % now)

    LoopingCall(dump_memory).start(PROFILE_MEMORY_INTERVAL, now=True)
    reactor.addSystemEventTrigger("before", "shutdown",
                                  lambda: scanner.dump_all_objects(path.join(memdump_dir, "memory-%06.2f-%s.out") % (
                                      time() - start, "-shutdown")))


def start_manhole():
    """
    Starts a manhole telnet server listening on MANHOLE_PORT
    """
    passwd_path = path.join(environ['PROJECT_DIR'], 'lib', 'passwd')
    global manhole
    manhole = manhole_tap.makeService({
        'namespace': manhole_namespace,
        'telnetPort': 'tcp:%d:interface=127.0.0.1' % MANHOLE_PORT,
        'sshPort': None,
        'passwd': passwd_path,
    })


#
# instrumentation.py ends here
