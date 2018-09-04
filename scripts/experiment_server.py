#!/usr/bin/env python3
# experiment_server.py ---
#
# Filename: experiment_server.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Sep  2 16:44:32 2013 (+0200)

# Commentary:
#
# %*% Experiment metainfo and time synchronization server.
# %*% TODO: Document this a bit more.
#
# It receives 3 types of commands:
# * time:<float>  -> Tells the service the local time for the subprocess for sync reasons.
# * set:key:value -> Sets an arbitrary variable associated with this connection to the
#                    specified value, can be used to share arbitrary data generated at
#                    startup between nodes just before starting the experiment.
# * ready         -> Indicates that this specific instance has ending sending its info
#                    and its ready to start.
#
# When the all of the instances we are waiting for are all ready, all the information will
# be sent back to them in the form of a JSON document. After this, a "go" command will
# be sent to indicate that they should start running the experiment.
#
# Example of an expected exchange:
# [connection is opened by the client]
# -> time:1378479678.11
# -> set:asdf:ooooo
# -> ready
# <- id:0
# <- {"0": {"host": "127.0.0.1", "time_offset": -0.94, "port": 12000, "asdf": "ooooo"}, "1": {"host": "127.0.0.1", "time_offset": "-1378479680.61", "port": 12001, "asdf": "ooooo"}, "2": {"host": "127.0.0.1", "time_offset": "-1378479682.26", "port": 12002, "asdf": "ooooo"}}
# <- go
# [Connection is closed by the server]


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

from os import environ

from gumby.sync import ExperimentServiceFactory
from gumby.log import setupLogging

from twisted.internet import reactor

# @CONF_OPTION SYNC_SUBSCRIBERS_AMOUNT: Number of sync clients we should wait for to be registered before starting the experiment. (default is DAS4_INSTANCES_TO_RUN)
# @CONF_OPTION SYNC_EXPERIMENT_START_DELAY: Delay the synchronized start of the experiment by this amount of seconds when giving the start signal.
# @CONF_OPTION SYNC_EXPERIMENT_START_DELAY: The default value should be OK for a few thousand instances. (float, default 5)
# @CONF_OPTION SYNC_PORT: Port where we should listen on. (required)

if __name__ == '__main__':
    setupLogging()
    if 'SYNC_SUBSCRIBERS_AMOUNT' in environ:
        expected_subscribers = int(environ['SYNC_SUBSCRIBERS_AMOUNT'])
    else:
        expected_subscribers = int(environ['DAS4_INSTANCES_TO_RUN'])

    experiment_start_delay = float(environ.get('SYNC_EXPERIMENT_START_DELAY', 5))
    server_port = int(environ['SYNC_PORT'])

    reactor.exitCode = 0
    reactor.listenTCP(server_port, ExperimentServiceFactory(expected_subscribers, experiment_start_delay))
    reactor.run()
    exit(reactor.exitCode)

#
# experiment_server.py ends here
