
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
# -> vars_received
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
import json
import logging
from time import time

from twisted.internet import reactor, task
from twisted.internet.defer import Deferred, DeferredSemaphore
from twisted.internet.protocol import (Factory, ReconnectingClientFactory, connectionDone)
from twisted.internet.threads import deferToThread
from twisted.protocols.basic import LineReceiver


EXPERIMENT_SYNC_TIMEOUT = 30

logger = logging.getLogger()

#
# Server side
#


class ExperimentServiceProto(LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, factory, id):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.id = id
        self.factory = factory
        self.ready = False
        self.state = 'init'
        self.vars = {}
        self.ready_d = None

    def connectionMade(self):
        self._logger.debug("New connection from: %s", str(self.transport.getPeer()))
        self.factory.setConnectionMade(self)

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found', self.state)
            stopReactor()
        else:
            self.state = statehandler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def sendAndWaitForReady(self):
        self.ready_d = Deferred()
        self.sendLine("id:%s" % self.id)
        return self.ready_d

    def connectionLost(self, reason=connectionDone):
        self._logger.debug("Lost connection with: %s with ID %s", str(self.transport.getPeer()), self.id)
        self.factory.unregisterConnection(self)
        LineReceiver.connectionLost(self, reason)

    #
    # Protocol state handlers
    #

    def proto_init(self, line):
        if line.startswith("time"):
            self.vars["time_offset"] = float(line.strip().split(':')[1]) - time()
            if abs(self.vars['time_offset']) < 0.5:  # ignore time_offset if smaller than +0.5/-0.5
                self.vars['time_offset'] = 0

            self._logger.debug("Time offset is %s", self.vars["time_offset"])
            return 'init'

        elif line.startswith('set:'):
            _, key, value = line.strip().split(':', 2)
            self._logger.debug("This subscriber sets %s to %s", key, value)
            self.vars[key] = value
            return 'init'

        elif line.strip() == 'ready':
            self._logger.debug("This subscriber is ready now.")
            self.ready = True
            self.factory.setConnectionReady(self)
            self.ready_d.callback(self)
            return 'vars_received'

        else:
            self._logger.error('Unexpected command received "%s"', line)
            self._logger.error('closing connection.')
            return 'done'

    def proto_vars_received(self, line):
        if line.strip() == 'vars_received':
            self.factory.setConnectionReceived(self)
            return "wait"
        self._logger.error('Unexpected command received "%s"', line)
        self._logger.error('closing connection.')
        return 'done'

    def proto_wait(self, line):
        self._logger.error('Unexpected command received "%s" while in ready state. Closing connection', line)
        return 'done'


class ExperimentServiceFactory(Factory):
    protocol = ExperimentServiceProto

    def __init__(self, expected_subscribers, experiment_start_delay):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.expected_subscribers = expected_subscribers
        self.experiment_start_delay = experiment_start_delay
        self.parsing_semaphore = DeferredSemaphore(500)
        self.connection_counter = -1
        self.connections_made = []
        self.connections_ready = []
        self.vars_received = []

        self._made_looping_call = None
        self._subscriber_looping_call = None
        self._subscriber_received_looping_call = None
        self._timeout_delayed_call = None

    def buildProtocol(self, addr):
        self.connection_counter += 1
        return ExperimentServiceProto(self, self.connection_counter + 1)

    def setConnectionMade(self, proto):
        if not self._timeout_delayed_call:
            self._timeout_delayed_call = reactor.callLater(EXPERIMENT_SYNC_TIMEOUT, self.onExperimentSetupTimeout)
        else:
            self._timeout_delayed_call.reset(EXPERIMENT_SYNC_TIMEOUT)

        self.connections_made.append(proto)
        if len(self.connections_made) >= self.expected_subscribers:
            self._logger.info("All subscribers connected!")
            if self._made_looping_call and self._made_looping_call.running:
                self._made_looping_call.stop()

            self.pushIdToSubscribers()
        else:
            if not self._made_looping_call:
                self._made_looping_call = task.LoopingCall(self._print_subscribers_made)
                self._made_looping_call.start(1.0)

    def _print_subscribers_made(self):
        if len(self.connections_made) < self.expected_subscribers:
            self._logger.info("%d of %d expected subscribers connected.", len(self.connections_made), self.expected_subscribers)

    def pushIdToSubscribers(self):
        for proto in self.connections_made:
            self.parsing_semaphore.run(proto.sendAndWaitForReady)

    def setConnectionReady(self, proto):
        self._timeout_delayed_call.reset(EXPERIMENT_SYNC_TIMEOUT)
        self.connections_ready.append(proto)

        if len(self.connections_ready) >= self.expected_subscribers:
            self._logger.info("All subscribers are ready, pushing data!")
            if self._subscriber_looping_call and self._subscriber_looping_call.running:
                self._subscriber_looping_call.stop()

            self.pushInfoToSubscribers()
        else:
            if not self._subscriber_looping_call:
                self._subscriber_looping_call = task.LoopingCall(self._print_subscribers_ready)
                self._subscriber_looping_call.start(1.0)

    def _print_subscribers_ready(self):
        self._logger.info("%d of %d expected subscribers ready.", len(self.connections_ready),
                          self.expected_subscribers)

    def pushInfoToSubscribers(self):
        # Generate the json doc
        vars = {}
        for subscriber in self.connections_ready:
            subscriber_vars = subscriber.vars.copy()
            subscriber_vars['port'] = subscriber.id + 12000
            subscriber_vars['host'] = subscriber.transport.getPeer().host
            vars[subscriber.id] = subscriber_vars

        json_vars = json.dumps(vars)
        del vars
        self._logger.info("Pushing a %d bytes long json doc.", len(json_vars))

        # Send the json doc to the subscribers
        task.cooperate(self._sendLineToAllGenerator(json_vars))

    def _sendLineToAllGenerator(self, line):
        for subscriber in self.connections_ready:
            yield subscriber.sendLine(line)

    def setConnectionReceived(self, proto):
        self._timeout_delayed_call.reset(EXPERIMENT_SYNC_TIMEOUT)
        self.vars_received.append(proto)

        if len(self.vars_received) >= self.expected_subscribers:
            self._logger.info("Data sent to all subscribers, giving the go signal in %f secs.",
                              self.experiment_start_delay)
            reactor.callLater(0, self.startExperiment)
            self._timeout_delayed_call.cancel()
        else:
            if not self._subscriber_received_looping_call:
                self._subscriber_received_looping_call = task.LoopingCall(self._print_subscribers_received)
                self._subscriber_received_looping_call.start(1.0)

    def _print_subscribers_received(self):
        self._logger.info("%d of %d expected subscribers received the data.", len(self.vars_received),
                          self.expected_subscribers)

    def startExperiment(self):
        # Give the go signal and disconnect
        self._logger.info("Starting the experiment!")

        if self._subscriber_received_looping_call and self._subscriber_received_looping_call.running:
            self._subscriber_received_looping_call.stop()

        start_time = time() + self.experiment_start_delay
        for subscriber in self.connections_ready:
            # Sync the experiment start time among instances
            subscriber.sendLine("go:%f" % (start_time + subscriber.vars['time_offset']))

        d = task.deferLater(reactor, 5, lambda: self._logger.info("Done, disconnecting all clients."))
        d.addCallback(lambda _: self.disconnectAll())
        d.addCallbacks(self.onExperimentStarted, self.onExperimentStartError)

    def disconnectAll(self):
        reactor.runUntilCurrent()

        def _disconnectAll():
            for subscriber in self.connections_ready:
                yield subscriber.transport.loseConnection()
        task.cooperate(_disconnectAll())

    def unregisterConnection(self, proto):
        if proto in self.connections_ready:
            self.connections_ready.remove(proto)
        if proto in self.vars_received:
            self.vars_received.remove(proto)
        if proto.id in self.vars_received:
            self.vars_received.remove(proto.id)

        self._logger.debug("Connection cleanly unregistered.")

    def onExperimentStarted(self, _):
        self._logger.info("Experiment started, shutting down sync server.")
        reactor.callLater(0, stopReactor)

    def onExperimentStartError(self, failure):
        self._logger.error("Failed to start experiment")
        reactor.exitCode = 1
        reactor.callLater(0, stopReactor)
        return failure

    def onExperimentSetupTimeout(self):
        self._logger.error("Waiting for all peers timed out, exiting.")
        reactor.exitCode = 1
        reactor.callLater(0, stopReactor)

    def lineLengthExceeded(self, line):
        self._logger.error("Line length exceeded, %d bytes remain.", len(line))
#
# Client side
#


class ExperimentClient(LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, vars):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.state = "id"
        self.my_id = None
        self.vars = vars
        self.all_vars = {}
        self.time_offset = None

    def connectionMade(self):
        self._logger.debug("Connected to the experiment server")
        self.sendLine("time:%f" % time())
        for key, val in self.vars.iteritems():
            self.sendLine("set:%s:%s" % (key, val))

        d = deferToThread(self.onVarsSend)
        self.state = "id"

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found', self.state)
            stopReactor()
        else:
            self.state = statehandler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def onVarsSend(self):
        self._logger.debug("onVarsSend: Call not implemented")

    def onIdReceived(self):
        self._logger.debug("onIdReceived: Call not implemented")

    def onAllVarsReceived(self):
        self._logger.debug("onAllVarsReceived: Call not implemented")

    def startExperiment(self):
        self._logger.debug("startExperiment: Call not implemented")

    def get_peer_id(self, ip, port):
        port = int(port)
        for peer_id, peer_dict in self.all_vars.iteritems():
            if peer_dict['host'] == ip and int(peer_dict['port']) == port:
                return peer_id

        self._logger.error("Could not get_peer_id for %s:%s", ip, port)

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
            self._logger.debug('Got id: "%s" assigned', id)
            d = deferToThread(self.onIdReceived)
            d.addCallback(lambda _: self.sendLine("ready"))
            return "all_vars"
        else:
            self._logger.error("Received an unexpected string from the server, closing connection")
            return "done"

    def proto_all_vars(self, line):
        self._logger.debug("Got experiment variables")

        self.all_vars = json.loads(line)
        self.time_offset = self.all_vars[self.my_id]["time_offset"]
        self.onAllVarsReceived()

        self.sendLine("vars_received")
        return "go"

    def proto_go(self, line):
        self._logger.debug("Got GO signal")
        if line.strip().startswith("go:"):
            start_delay = max(0, float(line.strip().split(":")[1]) - time())
            self._logger.info("Starting the experiment in %f secs.", start_delay)
            reactor.callLater(start_delay, self.startExperiment)
            self.factory.stopTrying()
            self.transport.loseConnection()


class ExperimentClientFactory(ReconnectingClientFactory):
    maxDelay = 10

    def __init__(self, vars, protocol=ExperimentClient):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.vars = vars
        self.protocol = protocol

    def buildProtocol(self, address):
        self._logger.debug("Attempting to connect to the experiment server.")
        p = self.protocol(self.vars)
        p.factory = self
        return p

    def clientConnectionFailed(self, connector, reason):
        self._logger.error("Failed to connect to experiment server (will retry in a while), error was: %s",
                           reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        self._logger.info("The connection with the experiment server was lost with reason: %s",
                          reason.getErrorMessage())

#
# Aux stuff
#


def stopReactor():
    if reactor.running:
        logger.debug("Stopping reactor")
        reactor.stop()

#
# sync.py ends here
