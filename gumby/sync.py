
# sync.py ---
#
# Filename: sync.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Sep  9 14:38:57 2013 (+0200)

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
# be sent back to them in the form of a JSON document. After this, a "go" command will
# be sent to indicate that they should start running the experiment with the absolute time at which the experiment should start.
#
# Example of an expected exchange:
# [connection is opened by the client]
# <- id:0
# -> time:1378479678.11
# -> set:asdf:ooooo
# -> ready
# <- {"0": {"host": "127.0.0.1", "time_offset": -0.94, "port": 12000, "asdf": "ooooo"}, "1": {"host": "127.0.0.1", "time_offset": "-1378479680.61", "port": 12001, "asdf": "ooooo"}, "2": {"host": "127.0.0.1", "time_offset": "-1378479682.26", "port": 12002, "asdf": "ooooo"}}
# <- go:1388665322.478153
# [Connection is closed by the server]
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

from time import time
import json
import logging

from twisted.internet import epollreactor
epollreactor.install()

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.defer import gatherResults
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory, ReconnectingClientFactory
from twisted.internet.task import deferLater
from twisted.internet.threads import deferToThread
from twisted.protocols.basic import LineReceiver
from twisted.python.log import msg, err

EXPERIMENT_SYNC_TIMEOUT = 60

#
# Server side
#


class ExperimentServiceProto(LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, factory, id):
        self.id = id
        self.factory = factory
        self.state = 'init'
        self.vars = {}

    def connectionMade(self):
        msg("New connection from: ", str(self.transport.getPeer()), logLevel=logging.DEBUG)

        self.sendLine("id:%s" % self.id)

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            err('Callback %s not found' % self.state)
            stopReactor()
        else:
            self.state = statehandler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def connectionLost(self, reason):
        msg("Lost connection with: %s with ID %s" % (str(self.transport.getPeer()), self.id), logLevel=logging.DEBUG)
        self.factory.unregisterConnection(self)
        LineReceiver.connectionLost(self, reason)

    #
    # Protocol state handlers
    #

    def proto_init(self, line):
        if line.startswith("time"):
            self.vars["time_offset"] = float(line.strip().split(':')[1]) - time()
            msg("Time offset is %s" % (self.vars["time_offset"]), logLevel=logging.DEBUG)
            return 'set'
        else:
            err("Haven't received the time command as the first line, closing connection")
            return 'done'

    def proto_set(self, line):
        if line.startswith('set:'):
            _, key, value = line.strip().split(':', 2)
            msg("This subscriber sets %s to %s" % (key, value), logLevel=logging.DEBUG)
            self.vars[key] = value
            return 'set'

        elif line.strip() == 'ready':
            msg("This subscriber is ready now.", logLevel=logging.DEBUG)
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

    def __init__(self, expected_subscribers, experiment_start_delay):
        self.expected_subscribers = expected_subscribers
        self.experiment_start_delay = experiment_start_delay
        self.connection_counter = -1
        self.connections = []
        self._timeout_delayed_call = None
        self._subscriber_looping_call = None

    def buildProtocol(self, addr):
        self.connection_counter += 1
        return ExperimentServiceProto(self, self.connection_counter + 1)

    def setConnectionReady(self, proto):
        if not self._timeout_delayed_call:
            self._timeout_delayed_call = reactor.callLater(EXPERIMENT_SYNC_TIMEOUT, self.onExperimentSetupTimeout)
        self.connections.append(proto)

        if len(self.connections) >= self.expected_subscribers:
            msg("All subscribers are ready, pushing data!")
            self._timeout_delayed_call.cancel()
            self.pushInfoToSubscribers()
        else:
            if not self._subscriber_looping_call:
                self._subscriber_looping_call = task.LoopingCall(self._print_subscribers_ready)
                self._subscriber_looping_call.start(1.0)

    def _print_subscribers_ready(self):
        if len(self.connections) < self.expected_subscribers:
            msg("%d of %d expected subscribers ready." % (len(self.connections), self.expected_subscribers))
        else:
            self._subscriber_looping_call.stop()

    def pushInfoToSubscribers(self):
        # Generate the json doc
        vars = {}
        for subscriber in self.connections:
            subscriber_vars = subscriber.vars.copy()
            subscriber_vars['port'] = subscriber.id + 12000
            subscriber_vars['host'] = subscriber.transport.getPeer().host
            vars[subscriber.id] = subscriber_vars

        json_vars = json.dumps(vars)
        json_part_size = 10 * 1024
        json_parts = [json_vars[i:i + json_part_size] for i in range(0, len(json_vars), json_part_size)]
        msg("Pushing a %d bytes long json doc. split into %d parts" % (len(json_vars), len(json_parts)))

        # Send the json doc to the subscribers
        for subscriber in self.connections:
            for json_part in json_parts:
                subscriber.sendLine(json_part)
        msg("Data sent to all subscribers, giving the go signal in %f secs." % self.experiment_start_delay)
        reactor.callLater(0, self.startExperiment)

    def startExperiment(self):
        # Give the go signal and disconnect
        msg("Starting the experiment!")
        deferreds = []
        start_time = time() + self.experiment_start_delay
        for subscriber in self.connections:
            # Sync the experiment start time among instances
            subscriber.sendLine("go:%f" % (start_time + subscriber.vars['time_offset']))
            deferreds.append(deferLater(reactor, 1, subscriber.transport.loseConnection))
        d = gatherResults(deferreds)
        d.addCallbacks(self.onExperimentStarted, self.onExperimentStartError)

    def unregisterConnection(self, proto):
        if proto in self.connections:
            self.connections.remove(proto)
        msg("Connection cleanly unregistered.", logLevel=logging.DEBUG)

    def onExperimentStarted(self, _):
        msg("Experiment started, shutting down sync server.")
        reactor.callLater(0, stopReactor)

    def onExperimentStartError(self, failure):
        err("Failed to start experiment")
        reactor.callLater(0, stopReactor)
        return failure

    def onExperimentSetupTimeout(self):
        err("Waiting for all peers timed out, exiting.")
        reactor.stop()

    def  lineLengthExceeded(self, line):
        err("Line length exceeded, %d bytes remain." % len(line))
#
# Client side
#


class ExperimentClient(LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, vars):
        self.state = "id"
        self.my_id = None
        self.vars = vars
        self.all_vars = ''
        self.time_offset = None

    def connectionMade(self):
        msg("Connected to the experiment server", logLevel=logging.DEBUG)
        self.sendLine("time:%f" % time())
        for key, val in self.vars.iteritems():
            self.sendLine("set:%s:%s" % (key, val))
        self.state = "id"

    def lineReceived(self, line):
        msg("received '%s'" % line[:20])

        if line.strip().startswith("go:"):
            self.state = "go"

        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            err('Callback %s not found' % self.state)
            stopReactor()
        else:
            self.state = statehandler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def onIdReceived(self):
        msg("onIdReceived: Call not implemented", logLevel=logging.DEBUG)

    def onAllVarsReceived(self):
        msg("onAllVarsReceived: Call not implemented", logLevel=logging.DEBUG)

    def startExperiment(self):
        msg("startExperiment: Call not implemented", logLevel=logging.DEBUG)

    def get_peer_id(self, ip, port):
        port = int(port)
        for peer_id, peer_dict in self.all_vars.iteritems():
            if peer_dict['host'] == ip and int(peer_dict['port']) == port:
                return peer_id

        err("Could not get_peer_id for", ip, port)

    def get_peer_ip_port_by_id(self, peer_id):
        if str(peer_id) in self.all_vars:
            return self.all_vars[str(peer_id)]['host'], self.all_vars[str(peer_id)]['port']

    def get_peers(self):
        return self.all_vars.keys()

    #
    # Protocol state handlers
    #

    def proto_id(self, line):
        # We should get a line such as:
        # id:SOMETHING
        maybe_id, id = line.strip().split(':', 1)
        if maybe_id == "id":
            self.my_id = id
            msg('Got id: "%s" assigned' % id, logLevel=logging.DEBUG)
            d = deferToThread(self.onIdReceived)
            d.addCallback(lambda _: self.sendLine("ready"))
            return "all_vars"
        else:
            err("Received an unexpected string from the server, closing connection")
            return "done"

    def proto_all_vars(self, line):
        msg("Got experiment variables")
        self.all_vars += line
        return "all_vars"

    def proto_go(self, line):
        msg("Got GO signal")

        self.all_vars = json.loads(self.all_vars)
        self.time_offset = self.all_vars[self.my_id]["time_offset"]
        self.onAllVarsReceived()

        if line.strip().startswith("go:"):
            start_delay = max(0, float(line.strip().split(":")[1]) - time())
            msg("Starting the experiment in %f secs." % start_delay)
            reactor.callLater(start_delay, self.startExperiment)
            self.factory.stopTrying()
            self.transport.loseConnection()


class ExperimentClientFactory(ReconnectingClientFactory):

    def __init__(self, vars, protocol=ExperimentClient):
        self.vars = vars
        self.protocol = protocol

    def buildProtocol(self, address):
        msg("Attempting to connect to the experiment server.", logLevel=logging.DEBUG)
        p = self.protocol(self.vars)
        p.factory = self
        return p

    def clientConnectionFailed(self, connector, reason):
        err("Failed to connect to experiment server (will retry in a while), error was: %s" % reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        msg("The connection with the experiment server was lost with reason: %s" % reason.getErrorMessage())

#
# Aux stuff
#


def stopReactor():
    if reactor.running:
        msg("Stopping reactor", logLevel=logging.DEBUG)
        reactor.stop()

#
# sync.py ends here
