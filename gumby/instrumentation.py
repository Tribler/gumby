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
import signal
from asyncio import get_event_loop
from os import environ, getpid, makedirs, path
from time import time

from gumby.util import run_task


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

PID = getpid()

logger = logging.getLogger()


def init_instrumentation():
    """
    Instrumentation initializer, starts the components enabled trough config options
    """
    if PROFILE_MEMORY and PROFILE_MEMORY_PID_MODULO and (PID % PROFILE_MEMORY_PID_MODULO == 0):
        start_memory_dumper()


def start_memory_dumper():
    """
    Initiates the memory profiler.
    """
    logger.info("starting memory dump looping call")
    try:
        from meliae import scanner
    except ImportError:
        logger.error("Meliae is not available on Python 3!")

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
                for sample_number in range(PROFILE_MEMORY_GRAPH_BACKREF_AMOUNT):
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

    run_task(dump_memory, interval=PROFILE_MEMORY_INTERVAL, delay=0)
    get_event_loop().add_signal_handler(signal.SIGTERM, lambda: scanner.dump_all_objects(
        path.join(memdump_dir, "memory-%06.2f-%s.out") % (time() - start, "-shutdown")))


#
# instrumentation.py ends here
