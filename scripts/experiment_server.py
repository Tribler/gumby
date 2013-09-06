#!/usr/bin/env python
# experiment_server.py ---
#
# Filename: experiment_server.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Sep  2 16:44:32 2013 (+0200)

# Commentary:
#
# Experiment metainfo and time synchronization server.
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
# be sent back to them in the form of a JSON document. After this, a "start" command will
# be sent to indicate that they should start running the experiment.
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

from getpass import getuser
from hashlib import md5
from sys import argv, exit, stdout
from threading import Lock
from time import time
import json

from twisted.internet import epollreactor
epollreactor.install()
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python.log import msg, err, startLogging


class ExperimentServiceProto(LineReceiver):

    def __init__(self, factory, id):
        self.id = id
        self.factory = factory
        self.state = 'init'
        self.vars = {}

    def connectionMade(self):
        msg("New connection from: ", str(self.transport.getPeer()))

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            crit('Callback %s not found' % self.state)
            reactor.stop()
        else:
            self.state = statehandler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def connectionLost(self, cosa):
        self.factory.unregisterConnection(self)
        LineReceiver.connectionLost(self, cosa)

    #
    # Protocol state handlers
    #

    def proto_init(self, line):
        if line.startswith("time"):
            self.vars["time_offset"] = str(float(line.strip().split(':')[1]) - time())
            msg("Time offset is %s" % (self.vars["time_offset"]))
            return 'set'
        else:
            err("Haven't received the time command as the first line, closing connection")
            return 'done'

    def proto_set(self, line):
            if line.startswith('set:'):
                _, key, value = line.strip().split(':')
                msg("This subscriber sets %s to %s" % (key, value))
                self.vars[key] = value
                return 'set'
            elif line.strip() == 'ready':
                msg("This subscriber is ready now.")
                self.ready = True
                self.factory.setConnectionReady(self)
                return 'wait'
            else:
                err('Unexpected command received "%s"' % line)
                err('closing connection.')
                return 'done'

    def proto_wait(self, line):
        err('Unexpected command received "%s" while in ready state. Closing connection' % line)
        return 'done'


class ExperimentServiceFactory(Factory):
    protocol = ExperimentServiceProto

    def __init__(self, expected_subscribers):
        self.expected_subscribers = expected_subscribers
        self.connection_counter = -1
        self.connections = []

    def buildProtocol(self, addr):
        self.connection_counter += 1
        return ExperimentServiceProto(self, self.connection_counter)

    def setConnectionReady(self, proto):
        self.connections.append(proto)
        if len(self.connections) >= self.expected_subscribers:
            msg("All subscribers are ready, pushing data!")
            self.pushInfoToSubscribers()
        else:
            msg("%d of %d expected subscribers ready." % (len(self.connections), self.expected_subscribers))

    def pushInfoToSubscribers(self):
        # Generate the json doc
        vars = {}
        for subscriber in self.connections:
            subscriber_vars = subscriber.vars.copy()
            subscriber_vars['port'] = subscriber.id + 12000
            subscriber_vars['host'] = subscriber.transport.getPeer().host
            vars[subscriber.id] = subscriber_vars
        json_vars = json.dumps(vars)

        # Send the ID and json doc to the subscribers
        for subscriber in self.connections:
            subscriber.sendLine("id:%s" % subscriber.id)
            subscriber.sendLine(json_vars)

        # Give the go signal and disconnect
        for subscriber in self.connections:
            subscriber.sendLine("go")
            reactor.callLater(0, subscriber.transport.loseConnection)

    def unregisterConnection(self, proto):
        if proto in self.connections:
            self.connections.remove(proto)
        msg("Connection cleanly unregistered.")


def main():
    startLogging(stdout)
    expected_subscribers = 3
    # initial_peer_delay = int(argv[2])
    server_port = 1222

    # server_port = int(md5sum.hexdigest()[-16:], 16) % 20000 + 15000

    reactor.listenTCP(server_port, ExperimentServiceFactory(expected_subscribers))
    reactor.run()

if __name__ == '__main__':
    main()


#
# experiment_server.py ends here
