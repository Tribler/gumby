
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
#
# After the initial time synchronization and experiment metainfo exchange, peers can send messages to each
# other using the synchronization server. This command looks like msg:<peer_id>:<message> where peer_id is the
# peer to which the message should be forwarded to.

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
from asyncio import Future, Semaphore, ensure_future, get_event_loop, sleep
from random import randint
from time import time

from gumby.experiment import ExperimentClient
from gumby.line_receiver import LineReceiver
from gumby.util import run_task

EXPERIMENT_SYNC_TIMEOUT = 30


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
        self.ready_future = Future()

    def connection_made(self, transport):
        super(ExperimentServiceProto, self).connection_made(transport)
        self._logger.debug("New connection from: %s", str(self.transport.get_extra_info('peername')))
        self.factory.set_connection_made(self)

    def line_received(self, line):
        try:
            pto = 'proto_' + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found', self.state)
            stop_loop()
        else:
            self.state = statehandler(line)

    def send_and_wait_for_ready(self):
        self.ready_future = Future()
        self.send_line(b"id:%d" % self.id)
        return self.ready_future

    def connection_lost(self, exc):
        self._logger.debug("Lost connection with: %s with ID %d", str(self.transport.get_extra_info('peername')),
                           self.id)
        self.factory.unregister_connection(self)
        LineReceiver.connection_lost(self, exc)

    #
    # Protocol state handlers
    #

    def proto_init(self, line):
        if line.startswith(b"time"):
            self.vars["time_offset"] = float(line.strip().split(b':')[1]) - time()
            if abs(self.vars['time_offset']) < 0.5:  # ignore time_offset if smaller than +0.5/-0.5
                self.vars['time_offset'] = 0

            self._logger.debug("Time offset is %s", self.vars["time_offset"])
            return 'init'

        elif line.startswith(b"set:"):
            _, key, value = line.strip().split(b':', 2)
            self._logger.debug("This subscriber sets %s to %s", key, value)
            self.vars[key.decode()] = value.decode()
            return 'init'

        elif line.strip() == b"ready":
            self._logger.debug("This subscriber is ready now.")
            self.ready = True
            self.factory.set_connection_ready(self)
            self.ready_future.set_result(self)
            return 'vars_received'

        else:
            self._logger.error('Unexpected command received "%s"', line)
            self._logger.error('closing connection.')
            return 'done'

    def proto_vars_received(self, line):
        if line.strip() == b"vars_received":
            self.factory.set_connection_received(self)
            return "wait"
        self._logger.error('Unexpected command received "%s"', line)
        self._logger.error('closing connection.')
        return 'done'

    def proto_wait(self, line):
        self._logger.error('Unexpected command received "%s" while in ready state. Closing connection', line)
        return 'done'

    def proto_running(self, line):
        if line.startswith(b"msg"):
            _, peer_id, msg_type, msg = line.strip().split(b':', 3)
            self._logger.debug("Received message with type %s for peer %s: %s",
                               msg_type.decode(), int(peer_id), msg.decode())

            # Forward the message to the appropriate peer
            self.factory.forwardMessage(self.id, int(peer_id), msg_type, msg)
        else:
            self._logger.error('Unexpected command received "%s" while in running state.', line)

        return "running"


class ExperimentServiceFactory:

    def __init__(self, expected_subscribers, experiment_start_delay):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.expected_subscribers = expected_subscribers
        self.experiment_start_delay = experiment_start_delay
        self.parsing_semaphore = Semaphore(500)
        self.connection_counter = -1
        self.connections_made = []
        self.connections_ready = []
        self.vars_received = []
        self.last_status_update = 0
        self.id_to_connection = {}

        self._timeout_delayed_call = None

    def __call__(self):
        self.connection_counter += 1
        return ExperimentServiceProto(self, self.connection_counter + 1)

    def reset_sync_timeout(self):
        if self._timeout_delayed_call:
            self._timeout_delayed_call.cancel()
        self._timeout_delayed_call = get_event_loop().call_later(EXPERIMENT_SYNC_TIMEOUT,
                                                                 self.on_experiment_setup_timeout)

    def set_connection_made(self, proto):
        self.reset_sync_timeout()
        self.connections_made.append(proto)

        if len(self.connections_made) == 1 or time() - self.last_status_update > 1:
            self._logger.info("%d of %d expected subscribers connected.",
                              len(self.connections_made), self.expected_subscribers)
            self.last_status_update = time()

        if len(self.connections_made) >= self.expected_subscribers:
            self._logger.info("All subscribers connected!")

            # Assign IDs to the connected subscribers, based on their address
            host_dict = {}
            for connection in self.connections_made:
                connection_host = connection.transport.get_extra_info('peername')[0]
                if connection_host not in host_dict:
                    host_dict[connection_host] = []
                host_dict[connection_host].append(connection)

            # Sort them on IP
            def split_ip(ip):
                return tuple(int(part) for part in ip.split('.'))

            def ip_addr_key(ip_addr):
                return split_ip(ip_addr)

            sorted_hosts = sorted(list(host_dict.keys()), key=ip_addr_key)

            # Assign
            cur_peer_index = 1
            cur_host_index = 0
            while cur_peer_index <= len(self.connections_made):
                # Get the next connection
                if host_dict[sorted_hosts[cur_host_index]]:
                    connection = host_dict[sorted_hosts[cur_host_index]].pop(0)
                    connection.id = cur_peer_index

                cur_host_index += 1
                cur_host_index %= len(sorted_hosts)
                cur_peer_index += 1

            ensure_future(self.push_id_to_subscribers())

    async def push_id_to_subscribers(self):
        for proto in self.connections_made:
            async with self.parsing_semaphore:
                await proto.send_and_wait_for_ready()

    def set_connection_ready(self, proto):
        self.reset_sync_timeout()
        self.connections_ready.append(proto)

        if len(self.connections_ready) == 1 or time() - self.last_status_update > 1:
            self._logger.info("%d of %d expected subscribers ready.",
                              len(self.connections_ready), self.expected_subscribers)
            self.last_status_update = time()

        if len(self.connections_ready) >= self.expected_subscribers:
            self._logger.info("All subscribers are ready, pushing data!")
            self.push_info_to_subscribers()

    def push_info_to_subscribers(self):
        # Generate the json doc
        vars = {}
        for subscriber in self.connections_ready:
            subscriber_vars = subscriber.vars.copy()
            if "port" not in subscriber_vars:
                subscriber_vars['port'] = subscriber.id + 12000
            if "host" not in subscriber_vars:
                subscriber_vars['host'] = subscriber.transport.get_extra_info('peername')[0]
            vars[subscriber.id] = subscriber_vars

        vars = {
            "server":
                {
                    "global_random": randint(0, (2 ** 32) - 1)
                },
            "clients": vars
        }
        json_vars = json.dumps(vars)
        del vars
        self._logger.info("Pushing a %d bytes long json doc.", len(json_vars))

        # Send the json doc to the subscribers
        self._send_line_to_all(json_vars.encode())

    def _send_line_to_all(self, line):
        for subscriber in self.connections_ready:
            subscriber.send_line(line)

    def set_connection_received(self, proto):
        self.reset_sync_timeout()
        self.vars_received.append(proto)

        if len(self.vars_received) == 1 or time() - self.last_status_update > 1:
            self._logger.info("%d of %d expected subscribers received the data.",
                              len(self.vars_received), self.expected_subscribers)
            self.last_status_update = time()

        if len(self.vars_received) >= self.expected_subscribers:
            self._logger.info("Data sent to all subscribers, giving the go signal in %.1f secs.",
                              self.experiment_start_delay)
            ensure_future(self.start_experiment())
            self._timeout_delayed_call.cancel()

    async def start_experiment(self):
        # Give the go signal and disconnect
        self._logger.info("Starting the experiment!")

        start_time = time() + self.experiment_start_delay
        for subscriber in self.connections_ready:
            # Sync the experiment start time among instances
            subscriber.send_line(b"go:%f" % (start_time + subscriber.vars['time_offset']))
            subscriber.state = "running"
            self.id_to_connection[subscriber.id] = subscriber

        await sleep(5)

    def forwardMessage(self, from_id, to_id, msg_type, msg):
        if to_id not in self.id_to_connection:
            self._logger.error("Error while forwarding message: peer with id %d not found!", to_id)

        self.id_to_connection[to_id].send_line(b"msg:%d:%s:%s" % (from_id, msg_type, msg))

    def disconnect_all(self):
        for subscriber in self.connections_ready:
            subscriber.transport.close()

    def unregister_connection(self, proto):
        if proto in self.connections_ready:
            self.connections_ready.remove(proto)
        if proto in self.vars_received:
            self.vars_received.remove(proto)
        if proto.id in self.vars_received:
            self.vars_received.remove(proto.id)

        self._logger.debug("Connection cleanly unregistered.")

    def on_experiment_started(self):
        self._logger.info("Experiment started, shutting down sync server.")
        get_event_loop().call_later(0, stop_loop, 0)

    def on_experiment_start_error(self, e):
        self._logger.error("Failed to start experiment")
        get_event_loop().call_later(0, stop_loop, 1)
        raise e

    def on_experiment_setup_timeout(self):
        self._logger.error("Waiting for all peers timed out, exiting.")
        get_event_loop().call_later(0, stop_loop, 1)

    def line_length_exceeded(self, line):
        super(ExperimentServiceFactory, self).line_length_exceeded(line)
        self._logger.error("Line length exceeded, %d bytes remain.", len(line))


class ExperimentClientFactory:

    def __init__(self, vars={}, protocol=ExperimentClient):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.vars = vars
        self.protocol = protocol
        self.reconnect_task = None
        self.reconnect = True

    def __call__(self):
        self._logger.debug("Attempting to connect to the experiment server.")
        p = self.protocol(self.vars)
        p.factory = self
        return p

    def stop_reconnecting(self):
        self.reconnect = False
        if self.reconnect_task:
            self.reconnect_task.cancel()

    def connection_lost(self, proto):
        if not self.reconnect:
            return

        self.reconnect_task = run_task(get_event_loop().create_connection,
                                       *proto.transport.get_extra_info('peername'), delay=10)


def stop_loop(exit_code=0):
    loop = get_event_loop()
    loop.exit_code = exit_code
    if loop.is_running():
        logging.getLogger().info("Stopping event loop")
        loop.stop()
