#!/usr/bin/env python3
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

import logging
import shlex
from os import environ, path
from re import compile as re_compile
from threading import RLock
from time import time

from twisted.internet import reactor


class ScenarioParser(object):
    """
    Scenario line format:
        TIMESPEC CALLABLE [ARGS] [PEERSPEC]

        TIMESPEC = [@][H:]M:S[-[H:]M:S]

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
    _re_substitution = re_compile("(\$\w+)")
    _re_preprocessor_dir = re_compile("^&(\w+)\s+")
    _re_named_arg = re_compile("^\s*(\w+)\s*=\s*(.*)$")

    def __init__(self):
        super(ScenarioParser, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self.file_lock = RLock()
        self.line_buffer = []
        self.preprocessor_callbacks = {
            "include": self._preproc_include_file
        }

    def add_scenario(self, filename):
        """
        Read the scenario into this scenario parser.
        """
        with self.file_lock:
            with open(filename, "r") as scenario_file:
                lines = scenario_file.readlines()

            line_number = 1
            for line in lines:
                if line.startswith("&"):
                    preproc_match = self._re_preprocessor_dir.match(line)
                    if preproc_match and preproc_match.group(1) in self.preprocessor_callbacks:
                        self.preprocessor_callbacks[preproc_match.group(1)](filename, line_number,
                                                                            line[preproc_match.end():].strip())
                    else:
                        self._logger.error("Error reading scenario %s:%d, preprocessor callback %s is unknown.",
                                           filename, line_number, line)
                elif not line.startswith('#'):
                    line = line.strip()
                    self.line_buffer.append((filename, line_number, line))
                line_number += 1

    def _preproc_include_file(self, filename, line_number, line):
        exline = self._expand_line(line)
        if not path.isabs(line):
            include_name = path.join(path.dirname(filename), exline)
        else:
            include_name = exline
        if not path.exists(include_name):
            include_name = path.join(environ["PROJECT_DIR"], exline)
        if not path.exists(include_name):
            include_name = path.join(environ["EXPERIMENT_DIR"], exline)
        if path.exists(include_name):
            self.add_scenario(include_name)
        else:
            self._logger.error("Error reading scenario %s:%d, include %s does not exist.", filename, line_number, line)

    def _parse_scenario(self):
        """
        Returns a list of commands that will be executed.

        A command is a (TIMESTAMP, FILENAME, LINENO, CALLABLE, ARGS, KWARGS) tuple. CALLABLE is
        the name of a function, method, etc. registered with this scenario using
        the register() method.
        """
        for filename, line_number, line in self.line_buffer:
            if line.endswith('}'):
                start = line.rfind('{') + 1
                peerspec = line[start:-1]
                line = line[:start - 1]
            else:
                peerspec = ''

            cmd = self._parse_scenario_line(filename, line_number, line, peerspec)
            if cmd is not None:
                yield cmd

    def _parse_scenario_line(self, filename, line_number, line, peerspec):
        """
        Parses one scenario line, and returns a command tuple. If a parsing
        error is encountered or the line should not be executed by this peer,
        returns None.

        The command tuple is described in _parse_scenario().
        """
        if self._parse_for_this_peer(peerspec):
            line = self._expand_line(line)
            try:
                parts = line.split(' ', 2)
                if len(parts) == 3:
                    timespec, callable, args = parts
                elif len(parts) == 1 and line.strip() == "":
                    return None
                else:
                    timespec, callable = parts
                    args = ''

                if timespec[0] == '@':
                    timespec = timespec[1:]
                timespec = timespec.split(':')
                begin = float(timespec[-1])
                if len(timespec) > 1:
                    begin += int(timespec[-2]) * 60
                if len(timespec) > 2:
                    begin += int(timespec[-3]) * 3600

                unnamed_args = []
                named_args = {}

                for arg in shlex.split(args):
                    argname = self._re_named_arg.match(arg)
                    if argname:
                        named_args[argname.group(1)] = arg[argname.start(2):]
                    else:
                        unnamed_args.append(arg)

                return begin, filename, line_number, callable, unnamed_args, named_args

            except Exception:
                self._logger.error("Error reading scenario %s:%d, invalid line %s.", filename, line_number, line,
                                   exc_info=True)

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

        if peerspec:
            if peerspec[0] == "!":
                peers = no_peers
                peerspec = peerspec[1:]
            else:
                peers = yes_peers

            for peer in peerspec.split(","):
                peer = peer.strip()
                if peer:
                    # parse the peer number (or peer number pair)
                    if "-" in peer:
                        low, high = peer.split("-")
                        peers.update(range(int(low), int(high) + 1))
                    else:
                        peers.add(int(peer))

        return yes_peers, no_peers

    def _parse_for_this_peer(self, peerspec):
        raise NotImplementedError('override this method please')

    def _expand_line(self, line):
        # Look for $VARIABLES to replace with config options from the env.
        for substitution in self._re_substitution.findall(line):
            if substitution[1:] in environ:
                line = line.replace(substitution, environ[substitution[1:]])

        return line


class ScenarioRunner(ScenarioParser):
    """
    Reads, parses and schedules events from scenario files.

    Use expstartstamp to synchronize all peers (usually you can get this from
    the gumby config server before starting the experiment). Each peer should
    set an unique peernumber.

    Users should register callables using register() before calling run(). All
    scenario events (lines) using unregistered callable names will be silently
    ignored. The callables will be executed on the main Twisted thread.
    """

    def __init__(self, expstartstamp=None):
        super(ScenarioRunner, self).__init__()
        self._callables = {}
        self._expstartstamp = expstartstamp

    def set_peernumber(self, peernumber):
        self._peernumber = peernumber

    def register(self, clb, name=None):
        """
        Registers callable to be used from a scenario file. An optional
        different name can be assigned.
        """
        if name is None:
            name = clb.__name__
        if name not in self._callables:
            self._callables[name] = []

        self._callables[name].append(clb)
        self._logger.debug("Registered callback %s target %s", name, clb)

    def run(self):
        """
        Schedules calls for each scenario line.
        """
        self._logger.info("Running scenario")

        if self._expstartstamp is None:
            self._expstartstamp = time()

        for tstmp, filename, line_number, clb, args, kwargs in self._parse_scenario():
            if clb not in self._callables:
                self._logger.error("Error running scenario %s:%d, undefined callback %s.", filename, line_number, clb)
                continue
            tstmp = tstmp + self._expstartstamp
            delay = tstmp - time()
            self._logger.info("Register call %s %s:%d %s %s %s", tstmp, filename, line_number, clb, repr(args), repr(kwargs))
            for target in self._callables[clb]:
                reactor.callLater(
                    delay if delay > 0.0 else 0,
                    target,
                    *args,
                    **kwargs
                )

    def _parse_for_this_peer(self, peerspec):
        if peerspec:
            yes_peers, no_peers = self._parse_peerspec(peerspec)
            return (
                not (yes_peers or no_peers) or
                (yes_peers and self._peernumber in yes_peers) or
                (no_peers and not self._peernumber in no_peers)
            )
        return True
