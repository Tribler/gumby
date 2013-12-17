#!/usr/bin/env python
# scenario.py ---
#
# Filename: scenario.py
# Description:
# Author: Boudewijn Schoon, Vlad Dumitrescu
# Maintainer:
# Created: Mon Jul  15 15:14:19 2013 (+0200)

# Commentary:
# This module parses events from a scenario file and schedules them on the main
# Twisted thread. Based on Dispersy's scenario parser by Boudewijn Schoon (uses
# the same syntax).
#
# Usage example:
#     t = Tribler(...)
#     t.start()
#     s = ScenarioRunner("./scenario", int(t.peerid))
#     s.register(t.test_method)
#     s.run()

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

from itertools import ifilter
from os import environ
from re import compile as re_compile
from time import time
import shlex
import sys

from twisted.internet import reactor
from twisted.python.log import msg, err

class ScenarioParser():
    """
    Scenario line format:
        TIMESPEC CALLABLE [ARGS] [PEERSPEC]

        TIMESPEC = [@+][H:]M:S[-[H:]M:S]

            Use @ to schedule events based on the synchronized experiment starting timestamp.

        CALLABLE = string

            Name of a callable previously registered using register()

        ARGS = ARG1 [ARG2 ..]

            Each arg of the callable as a string. The callable should handle
            conversions to the proper type.

        PEERSPEC = {PEERNR1 [, PEERNR2, ...] [, PEERNR3-PEERNR6, ...]}

            Examples: "{1,2}" - apply event only for peer 1 and 2, "{3-6}" - apply
            event for peers 3 to 6 (including 3 and 6).
            Moreover, if the PEERSPEC starts with an !, the event will apply
            for all peers except those specified.

        Notes:
             - Have in mind that in case of having several lines with the same
               time stamp, they will be executed in order.
    """
    _re_line = re_compile(
        r"^"
        r"@?"
        r"\s*"
        r"(?:(?P<beginH>\d+):)?(?P<beginM>\d+):(?P<beginS>\d+)"
        r"\s+"
        r"(?P<callable>\w+)(?P<args>\s+(.+?))??"
        r"(?:\s*"
        r"{(?P<peers>\s*!?\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*\s*)}"
        r")?\s*(?:\n)?$"
    )
    _re_substitution = re_compile("(\$\w+)")

    # TODO(emilon): We should make the minutes and its colon optional, so we can just use secs.

    def _parse_scenario(self, filename):
        """
        Returns a list of commands that will be executed.

        A command is a (TIMESTAMP, LINENO, CALLABLE, ARGS) tuple. CALLABLE is
        the name of a function, method, etc. registered with this scenario using
        the register() method.
        """
        try:
            for lineno, line in enumerate(open(filename, "r")):
                if not line.startswith('#'):
                    cmd = self._parse_scenario_line(lineno + 1, line)
                    if cmd is not None:
                        yield cmd
        except EnvironmentError:
            print >> sys.stderr, "Scenario file open/read error", filename

    def _parse_scenario_line(self, lineno, line):
        """
        Parses one scenario line, and returns a command tuple. If a parsing
        error is encountered or the line should not be executed by this peer,
        returns None.

        The command tuple is described in _parse_scenario().
        """
        match = self._re_line.match(self._preprocess_line(line))
        if match:
            # remove all entries that are None (to get default per key)
            dic = dict(ifilter(
                lambda key_value: key_value[1] is not None,
                match.groupdict().iteritems()
            ))

            # only return lines that belong to this peer
            peerspec = self._parse_peerspec(dic.get("peers", ""))
            if self._parse_for_this_peer(peerspec):
                begin = int(dic.get("beginH", 0)) * 3600.0 + \
                    int(dic.get("beginM", 0)) * 60.0 + \
                    int(dic.get("beginS", 0))
                return (
                    begin,
                    lineno,
                    dic.get("callable", ""),
                    tuple(shlex.split(dic.get("args", ""))),
                    peerspec
                )
        elif line.strip():
            print >> sys.stderr, "Ignoring invalid scenario line", lineno

        # line not for this peer or a parse error occurred
        return None

    def _parse_peerspec(self, peerspec):
        """
        Checks if current peernumber matches a peer specification.

        A peer specification if formatted as:
            [{PEERNR1 [, PEERNR2, ...] [, PEERNR3-PEERNR6, ...]}]

        Note: An empty peer specification matches everything.
        """
        # get individual peers, if any, for a peer spec
        yes_peers = set()
        no_peers = set()

        if peerspec.startswith("!"):
            peers = no_peers
        else:
            peers = yes_peers

        for peer in peerspec.split(","):
            peer = peer.strip()
            if peer:
                # parse the peer number (or peer number pair)
                if "-" in peer:
                    low, high = peer.split("-")
                    peers.update(xrange(int(low), int(high) + 1))
                else:
                    peers.add(int(peer))

        return yes_peers, no_peers

    def _parse_for_this_peer(self):
        raise NotImplementedError('override this method please')

    def _preprocess_line(self, line):
        # Look for $VARIABLES to replace with config options from the env.
        for substitution in self._re_substitution.findall(line):
            if substitution[1:] in environ:
                line = line.replace(substitution, environ[substitution[1:]])

        return line

class ScenarioRunner(ScenarioParser):

    """
    Reads, parses and schedules events from scenario file.

    Use expstartstamp to synchronize all peers (usually you can get this from
    the gumby config server before starting the experiment). Each peer should
    set an unique peernumber.

    Users should register callables using register() before calling run(). All
    scenario events (lines) using unregistered callable names will be silently
    ignored. The callables will be executed on the main Twisted thread.
    """

    def __init__(self, filename, peernumber, expstartstamp=None):
        self.filename = filename

        self._callables = {}
        self._expstartstamp = expstartstamp
        self._peernumber = peernumber
        self._origin = None  # will be set just before run()-ing

    def register(self, clb, name=None):
        """
        Registers callable to be used from a scenario file. An optional
        different name can be assigned.
        """
        if name is None:
            name = clb.__name__
        self._callables[name] = clb

    def run(self):
        """
        Schedules calls for each scenario line.
        """
        msg("Running scenario from file:", self.filename)

        if self._expstartstamp == None:
            self._expstartstamp = time()

        for (tstmp, lineno, clb, args, peerspec) in self._parse_scenario(self.filename):
            if clb not in self._callables:
                err(clb, "is not registered as an action!")
                continue

            tstmp = tstmp + self._expstartstamp
            delay = tstmp - time()
            reactor.callLater(
                delay if delay > 0.0 else 0,
                self._callables[clb],
                *args
            )

    def _parse_for_this_peer(self, peerspec):
        yes_peers, no_peers = peerspec
        return (
            not (yes_peers or no_peers) or
            (yes_peers and self._peernumber in yes_peers) or
            (no_peers and not self._peernumber in no_peers)
        )

#
# scenario.py ends here
