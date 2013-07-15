#!/usr/bin/env python
# scenario.py ---
#
# Filename: scenario.py
# Description:
# Author: Boudewijn Schoon, Vlad Dumitrescu
# Maintainer:
# Created: Mon Jul  15 15:14:19 2013 (+0200)

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

"""Parses and runs scenarios."""

import sys
from time import time
from itertools import ifilter
from random import random
from threading import Thread
from re import compile as re_compile

class ScenarioRunner(Thread):
    """
    Reads, parses and schedules events from scenario file in a separate thread.
    
    Use expstartstamp to synchronize all peers (usually you can get this from
    the gumby config server before starting the experiment). Each peer should
    set an unique peernumber.

    Users should register callables using register() before calling start() on
    this thread. All scenario events (lines) using unregistered callable names
    will be silently ignored. Also, the callables should be thread-safe since
    they will be executed on separate Twisted threads (because users might want
    to execute concurrent actions).

    Scenario line format:
        TIMESPEC CALLABLE [ARGS] [PEERSPEC]

        TIMESPEC = [@+][H:]M:S[-[H:]M:S]
        
            Use @ to schedule events based on experiment startstamp (use this to
            synchronize all peers) - recommended and default. Use + to schedule
            events based on peer's startime. Using just [H:]M:S will schedule
            event hours:minutes:seconds after @ or +, while [H:]M:S-[H:]M:S will
            schedule at a random time in that interval.
        
        CALLABLE = string

            Name of a callable previously registered using register()

        ARGS = ARG1 [ARG2 ..]

            Each arg of the callable as a string. The callable should handle
            conversions to the proper type.

        PEERSPEC = {PEERNR1 [, PEERNR2, ...] [, PEERNR3-PEERNR6, ...]}

            Examples: "1,2" - apply event only for peer 1 and 2, 3-6 - apply
            event for peers 3 to 6 (including 3 and 6).
    """
    def __init__(self, filename, peernumber, expstartstamp=None):
        super(ScenarioRunner, self).__init__(name="ScenarioRunner")
        self.filename = filename

        self._functions = {}
        self._expstartstamp = expstartstamp
        self._peernumber = peernumber
        self._re_line = re_compile(
            r"^"
            r"(?P<origin>[@+])"
            r"\s*"
            r"(?:(?P<beginH>\d+):)?(?P<beginM>\d+):(?P<beginS>\d+)"
            r"(?:\s*-\s*"
            r"(?:(?P<endH>\d+):)?(?P<endM>\d+):(?P<endS>\d+)"
            r")?"
            r"\s+"
            r"(?P<callable>\w+)(?P<args>\s+(.+?))??"
            r"(?:\s*"
            r"{(?P<peers>\s*!?\d+(?:-\d+)?(?:\s*,\s*!?\d+(?:-\d+)?)*\s*)}"
            r")?\s*(?:\n)?$"
        )
        self._origin = None # will be set just before starting the thread

    def register(self, clb, name=None):
        """
        Registers callable to be used from a scenario file. An optional
        different name can be assigned.
        """
        if name is None:
            name = clb.__name__
        self._functions[name] = clb

    def start(self):
        # initialize origin start times
        # _parse_scenario_line() will choose one of them for each lines
        now = time()
        self._origin = {
            "@" : float(self._expstartstamp)
                if self._expstartstamp is not None else now,
            "+" : now
        }
        super(ScenarioRunner, self).start() 

    def run(self):
        print "Running scenario from file:", self.filename

        for cmd in self._parse_scenario(self.filename):
            print cmd
            # TODO(vladum): Schedule calls on Twisted.

    # TODO(vladum): Move _parse_*() stuff to separate class.

    def _parse_scenario(self, filename):
        """
        Returns a list of commands that will be executed.

        A command is a (TIMESTAMP, LINENO, CALLABLE, ARGS) tuple. CALLABLE is
        the name of a function, method, etc. registered with this scenario using
        the register() method.
        """
        commands = []
        try:
            for lineno, line in enumerate(open(filename, "r")):
                cmd = self._parse_scenario_line(lineno, line)
                if cmd is not None:
                    commands.append(cmd)
        except EnvironmentError:
            print >> sys.stderr, "Cannot open/read scenario file", filename
        return commands

    def _parse_scenario_line(self, lineno, line):
        """
        Parses one scenario line, and returns a command tuple. If a parsing
        error is encountered or the line should not be executed by this peer,
        returns None.

        The command tuple is described in _parse_scenario().
        """
        match = self._re_line.match(line)
        if match:
            # remove all entries that are None (to get default per key)
            dic = dict(ifilter(
                lambda key, value: value is not None,
                match.groupdict().iteritems()
            ))

            # only return lines that belong to this peer
            if self._parse_for_this_peer(dic.get("peers", "")):
                begin = int(dic.get("beginH", 0)) * 3600.0 + \
                        int(dic.get("beginM", 0)) * 60.0 + \
                        int(dic.get("beginS", 0))
                end = int(dic.get("endH", 0)) * 3600.0 + \
                      int(dic.get("endM", 0)) * 60.0 + \
                      int(dic.get("endS", 0))
                assert end == 0.0 or begin <= end, \
                       "if given, end time must be at or after the start time"
                timestamp = self._origin[dic.get("origin", "@")] + \
                            begin + \
                            (random() * (end - begin) if end else 0.0)
                return (
                    timestamp,
                    lineno,
                    dic.get("callable", ""),
                    tuple(dic.get("args", "").split())
                )
        else:
            print >> sys.stderr, "Ignoring invalid scenario line", lineno

        # line not for this peer or a parse error occurred
        return None

    def _parse_for_this_peer(self, peerspec):
        """
        Checks if current peernumber matches a peer specification.

        A peer specification if formatted as:
            [{PEERNR1 [, PEERNR2, ...] [, PEERNR3-PEERNR6, ...]}]

        Note: An empty peer specification matches everything.
        """
        # get individual peers, if any, for a peer spec
        yes_peers = set()
        no_peers = set()
        for peer in peerspec.split(","):
            peer = peer.strip()
            if peer:
                # if the peer number (or peer number pair) is preceded by '!' it
                # negates the result
                if peer.startswith("!"):
                    peer = peer[1:]
                    peers = no_peers
                else:
                    peers = yes_peers
                # parse the peer number (or peer number pair)
                if "-" in peer:
                    low, high = peer.split("-")
                    peers.update(xrange(int(low), int(high)+1))
                else:
                    peers.add(int(peer))
        return (
            not (yes_peers or no_peers) or 
            (yes_peers and self._peernumber in yes_peers) or
            (no_peers and not self._peernumber in no_peers)
        )

#
# scenario.py ends here
