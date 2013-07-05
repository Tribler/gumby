# sshrunner.py ---
#
# Filename: sshrunner.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon May 27 20:19:26 2013 (+0200)

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

import sys
import os

from zope.interface import implements

from twisted.python.log import err, msg, Logger
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.error import ConnectionDone, ProcessTerminated
from twisted.internet.defer import Deferred, DeferredList, succeed, setDebugging
from twisted.internet.interfaces import IStreamClientEndpoint
from twisted.internet.protocol import Factory, Protocol, ClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint

from twisted.conch.ssh.common import NS
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.ssh.transport import SSHClientTransport
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.client.default import SSHUserAuthClient
from twisted.conch.client.options import ConchOptions

from struct import unpack

#setDebugging(True)

class _CommandTransport(SSHClientTransport):
    _secured = False

    def verifyHostKey(self, hostKey, fingerprint):
        # TODO: we should check the key
        return succeed(True)

    def connectionSecure(self):
        self._secured = True
        connection = _CommandConnection(self.factory.command)
        self.connection = connection
        userauth = SSHUserAuthClient(
            self.factory.user,
            ConchOptions(),
            connection)
        self.requestService(userauth)

    def connectionLost(self, reason):
        msg("Connection lost with reason:", reason)
        if self._secured and reason.type is ConnectionDone:
            if isinstance(self.connection.reason, ProcessTerminated):
                reason = Failure(self.connection.reason)
            else:
                reason = None
        self.factory.finished.callback(reason)


class _CommandConnection(SSHConnection):
    def __init__(self, command):
        SSHConnection.__init__(self)
        self.command_str = command
        self.reason = None

    def serviceStarted(self):
        channel = _CommandChannel(self.command_str, conn=self)
        self.openChannel(channel)

    def channelClosed(self, channel):
        SSHConnection.channelClosed(self, channel)
        self.reason = channel.reason
        self.transport.loseConnection()


class _CommandChannel(SSHChannel):
    name = 'session'

    def __init__(self, command, **k):
        SSHChannel.__init__(self, **k)
        self.command = command
        self.reason = None

    # def openFailed(self, reason):
    #     self._commandConnected.errback(reason)

    def channelOpen(self, _):
        self.conn.sendRequest(self, 'exec', NS(self.command))

    def dataReceived(self, bytes_):
        # we could recv more than 1 line
        for line in bytes_[:-1].replace("\r\n", "\n").split("\n"):
            msg('SSH "%s" STDOUT: %s' % (self.command, line))

    def extReceived(self, _, bytes_):
        # we could recv more than 1 line
        for line in bytes_[:-1].replace("\r\n", "\n").split("\n"):
            msg('SSH "%s" STDERR: %s' % (self.command, line))

    def closed(self):
        msg("SSH command channel closed")
        if not self.reason:
            # No command failure
            self.reason = ConnectionDone("ssh channel closed")

    def request_exit_status(self, data):
        """
        When the server sends the command's exit status, record it for later
        delivery to the protocol.

        @param data: The network-order four byte representation of the exit
            status of the command.
        @type data: L{bytes}
        """
        (status,) = unpack('>L', data)
        if status != 0:
            self.reason = ProcessTerminated(status, None, None)

    def request_exit_signal(self, data):
        """
        When the server sends the command's exit status, record it for later
        delivery to the protocol.

        @param data: The network-order four byte representation of the exit
            signal of the command.
        @type data: L{bytes}
        """
        (signal,) = unpack('>L', data)
        self.reason = ProcessTerminated(None, signal, None)


class CommandFactory(ClientFactory):
    def __init__(self, command, user):
        self.command = command
        self.user = user
        self.protocol = _CommandTransport
        self.finished = Deferred()

    def clientConnectionLost(self, connector, reason):
        msg("Client connection lost:", connector, reason, reason.type)
        if not self.finished.called:  # TODO: This could be prettier
            if reason.type is ConnectionDone:
                self.finished.callback(None)
            else:
                self.finished.errback(reason)


def runRemoteCMD(host, command):
    def checkExitStatus(reason):
        if reason:
            return reason
            # if reason.type is ConnectionDone:
            #     return 0
            # elif reason.type is ProcessTerminated:
            #     if reason.value.exitCode:
            #         return reason.value.exitCode
            #     else:
            #         return -reason.value.signal

    if '@' in host:
        user, host = host.split('@')
    else:
        user = os.environ['USER']
    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    else:
        port = 22

    factory = CommandFactory(command, user)
    reactor.connectTCP(host, port, factory)

    factory.finished.addBoth(checkExitStatus)
    return factory.finished

#
# sshrunner.py ends here
