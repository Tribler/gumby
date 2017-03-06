
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
from collections import Iterable
from os import environ, path, makedirs, chdir

from twisted.internet import reactor, task
from twisted.internet.defer import Deferred, DeferredSemaphore
from twisted.internet.protocol import (Factory, ReconnectingClientFactory, connectionDone)
from twisted.internet.threads import deferToThread
from twisted.protocols.basic import LineReceiver

from gumby.scenario import ScenarioRunner
from gumby.modules.experiment_module import ExperimentModule


EXPERIMENT_SYNC_TIMEOUT = 30

logger = logging.getLogger()


#
# Aux stuff
#


def stop_reactor():
    if reactor.running:
        logger.debug("Stopping reactor")
        reactor.stop()


def experiment_callback(name=None):
    def experiment_callback_wrapper(f):
        f.register_as_callback = name if name is not None and not callable(name) else f.__name__
        return f
    if callable(name):
        return experiment_callback_wrapper(name)
    else:
        return experiment_callback_wrapper


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
            stop_reactor()
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
            if "port" not in subscriber_vars:
                subscriber_vars['port'] = subscriber.id + 12000
            if "host" not in subscriber_vars:
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
        reactor.callLater(0, stop_reactor)

    def onExperimentStartError(self, failure):
        self._logger.error("Failed to start experiment")
        reactor.exitCode = 1
        reactor.callLater(0, stop_reactor)
        return failure

    def onExperimentSetupTimeout(self):
        self._logger.error("Waiting for all peers timed out, exiting.")
        reactor.exitCode = 1
        reactor.callLater(0, stop_reactor)

    def lineLengthExceeded(self, line):
        self._logger.error("Line length exceeded, %d bytes remain.", len(line))

#
# Client side
#
class ExperimentClient(object, LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, vars):
        super(ExperimentClient, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

        self.state = "id"
        self.my_id = None
        self.vars = vars
        self.all_vars = {}
        self.time_offset = None
        self.scenario_runner = ScenarioRunner()
        self.scenario_runner.preprocessor_callbacks["module"] = self._preproc_module
        self.loaded_experiment_module_classes = []
        self.experiment_modules = []
        self._stats_file = None
        if not hasattr(self, 'scenario_file'):
            self.scenario_file = environ.get("SCENARIO_FILE", None)

        self.register_callbacks(self)

        if self.scenario_file is None:
            self._logger.error("No Scenario file defined, starting empty experiment")
        else:
            if not path.exists(self.scenario_file):
                self._logger.info("Scenario file %s not found, attempting scenario file in experiment dir",
                                  self.scenario_file)
                self.scenario_file = path.join(environ['EXPERIMENT_DIR'], self.scenario_file)
            if path.exists(self.scenario_file):
                self.scenario_runner.add_scenario(self.scenario_file)
            else:
                self._logger.info("Scenario file %s not found", self.scenario_file)

    def connectionMade(self):
        self._logger.debug("Connected to the experiment server")
        self.sendLine("time:%f" % time())

        self.state = "id"

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            state_handler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found', self.state)
            stop_reactor()
        else:
            self.state = state_handler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def on_id_received(self):
        self.scenario_runner.set_peernumber(self.my_id)

        my_dir = path.join(environ['OUTPUT_DIR'], str(self.my_id))
        if path.exists(my_dir):
            self._logger.warning("Output directory already exists, should you clean before experiment? (%s)", my_dir)
        else:
            makedirs(my_dir)
        chdir(my_dir)
        self._stats_file = open("statistics.log", 'w')

        for m in self.experiment_modules:
            m.on_id_received()

        for key, val in self.vars.iteritems():
            self.sendLine("set:%s:%s" % (key, val))

    def on_all_vars_received(self):
        pass

    def start_experiment(self):
        self.scenario_runner.run()

    def get_peer_id(self, ip, port):
        port = int(port)
        for peer_id, peer_dict in self.all_vars.iteritems():
            if peer_dict['host'] == ip and int(peer_dict['port']) == port:
                return peer_id

        self._logger.error("Could not get_peer_id for %s:%s", ip, port)

    def get_peer_ip_port_by_id(self, peer_id):
        if str(peer_id) in self.all_vars:
            return str(self.all_vars[str(peer_id)]['host']), self.all_vars[str(peer_id)]['port']

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
            self.my_id = int(id)
            self._logger.debug('Got assigned id: %s', id)
            d = deferToThread(self.on_id_received)
            d.addCallback(lambda _: self.sendLine("ready"))
            return "all_vars"
        else:
            self._logger.error("Received an unexpected string from the server, closing connection")
            return "done"

    def proto_all_vars(self, line):
        self._logger.debug("Got experiment variables")

        self.all_vars = json.loads(line)
        self.time_offset = self.all_vars[str(self.my_id)]["time_offset"]
        self.on_all_vars_received()

        self.sendLine("vars_received")
        return "go"

    def proto_go(self, line):
        self._logger.debug("Got GO signal")
        if line.strip().startswith("go:"):
            start_delay = max(0, float(line.strip().split(":")[1]) - time())
            self._logger.info("Starting the experiment in %f secs.", start_delay)
            reactor.callLater(start_delay, self.start_experiment)
            self.factory.stopTrying()
            self.transport.loseConnection()

    def register_callbacks(self, module):
        member_names = [name for name in dir(module) if type(getattr(module.__class__, name, None)).__name__ != "property"]
        for member in [getattr(module, key) for key in member_names]:
            if not (callable(member) and hasattr(member, "register_as_callback")):
                continue
            else:
                self.scenario_runner.register(member, name=member.register_as_callback)

    @experiment_callback
    def echo(self, *argv):
        self._logger.info("%s ECHO %s", self.my_id, ' '.join(argv))

    @experiment_callback
    def annotate(self, message):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "annotate", message))

    @experiment_callback
    def peertype(self, peer_type):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "peertype", peer_type))

    @experiment_callback
    def stop(self):
        stop_reactor()

    def print_on_change(self, name, prev_dict, cur_dict):
        def get_changed_values(prev_dict, cur_dict):
            new_values = {}
            changed_values = {}
            if cur_dict:
                for key, value in cur_dict.iteritems():
                    # convert key to make it printable
                    if not isinstance(key, (basestring, int, long, float)):
                        key = str(key)

                    # if this is a dict, recursively check for changed values
                    if isinstance(value, dict):
                        converted_dict, changed_in_dict = get_changed_values(prev_dict.get(key, {}), value)

                        new_values[key] = converted_dict
                        if changed_in_dict:
                            changed_values[key] = changed_in_dict

                    # else convert and compare single value
                    else:
                        if not isinstance(value, (basestring, int, long, float, Iterable)):
                            value = str(value)

                        new_values[key] = value
                        if prev_dict.get(key, None) != value:
                            changed_values[key] = value

            return new_values, changed_values

        new_values, changed_values = get_changed_values(prev_dict, cur_dict)
        if changed_values:
            self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, name, json.dumps(changed_values)))
            self._stats_file.flush()
            return new_values
        return prev_dict

    def _preproc_module(self, filename, line_number, line):
        (modulename, _, classname) = line.rpartition('.')
        if modulename is None or modulename == "":
            try:
                stuff = __import__(__package__, fromlist=[classname])
            except:
                self._logger.info("Unable to import %s (from %s:%d)", line, filename, line_number, exc_info=True)
                try:
                    stuff = __import__(classname)
                except:
                    self._logger.error("Unable to import %s (from %s:%d)", line, filename, line_number, exc_info=True)
                    stuff = None
        else:
            try:
                stuff = __import__(modulename, fromlist=[classname])
            except:
                self._logger.error("Unable to import %s (from %s:%d)", line, filename, line_number, exc_info=True)
                stuff = None

        for item in [getattr(stuff, item_key) for item_key in dir(stuff)]:
            if not isinstance(item, type) or \
                    not issubclass(item, ExperimentModule) or \
                    item is ExperimentModule or \
                    item in self.loaded_experiment_module_classes:
                continue
            self.loaded_experiment_module_classes.append(item)
            if hasattr(item, "on_module_load") and callable(item.on_module_load):
                item.on_module_load(self)


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

