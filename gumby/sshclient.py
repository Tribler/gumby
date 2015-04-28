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

import os
import logging

from twisted.python.log import err, msg
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.error import ConnectionDone, ProcessTerminated, ConnectionLost
from twisted.internet.defer import Deferred, DeferredList, succeed, setDebugging
from twisted.internet.protocol import ClientFactory

from twisted.conch.ssh.common import NS
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.ssh.transport import SSHClientTransport
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.client.default import SSHUserAuthClient
from twisted.conch.client.options import ConchOptions
from twisted.conch.ssh.session import packRequest_pty_req

from struct import unpack, pack

# setDebugging(True)

_ERROR_REASONS = (
    ProcessTerminated,
    ConnectionLost
)


class _CommandTransport(SSHClientTransport):
    _secured = False

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

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
        nreason = None
        if self._secured and reason.type is ConnectionDone:
            if isinstance(self.connection.reason, _ERROR_REASONS):
                nreason = Failure(self.connection.reason)
        if nreason is not None:
            err("Connection lost with reason: %s" % self.connection.reason)
        else:
            self._logger.info("Connection lost with reason: %s", reason)

        self.factory.finished.callback(nreason)

    def receiveError(self, reason, desc):
        err_msg = "Received error: %s (reasonCode=%d)" % (desc, reason)
        err(err_msg)
        self.connection.reason = ConnectionLost(err_msg)


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

        self._logger = logging.getLogger(self.__class__.__name__)

        self._databytes = ''
        self._extbytes = ''
        self.command = command
        self.reason = None

    # def openFailed(self, reason):
    #     self._commandConnected.errback(reason)

    def channelOpen(self, _):

        def ptyReqFailed(reason):
            # TODO(vladum): Why is this never called? Looks like the Transport
            # received the error (at least the packet integrity ones).
            err("SSH PTY Request failed")
            self.reason = reason
            self.conn.sendClose(self)
            return reason

        # First request the TTY
        modes = pack("<B", 0x00)  # only TTY_OP_END
        win_size = (0, 0, 0, 0)  # 0s are ignored
        pty_req_data = packRequest_pty_req('vt100', win_size, modes)
        d = self.conn.sendRequest(self, 'pty-req', pty_req_data, wantReply=True)
        d.addErrback(ptyReqFailed)

        # And now we are ready to run the command
        d.addCallback(
            # Send command after we get the pty
            lambda _: self.conn.sendRequest(self, 'exec', NS(self.command))
        )

    # TODO(emilon): Refactor this to a generic function to be used by dataReceived, extReceived and the OneshotProcessProtocol.
    def dataReceived(self, bytes_):
        # we could recv more than 1 line and or a partial line.
        self._databytes += bytes_.replace('\r\n', '\n')
        remainder = ""
        for line in self._databytes.splitlines(True):
            if line.endswith('\n'):
                self._logger.info('SSH "%s" STDOUT: %s', self.command, line.rstrip())
            else:
                # It's a partial line (part of the last one), save it to the buffer instead
                remainder = line
        self._databytes = remainder

    def extReceived(self, _, bytes_):
        # we could recv more than 1 line and or a partial line.
        self._extbytes += bytes_.replace('\r\n', '\n')
        remainder = ""
        for line in self._extbytes.splitlines(True):
            if line.endswith('\n'):
                self._logger.info('SSH "%s" STDERR: %s', self.command, line.rstrip())
            else:
                # It's a partial line (part of the last one), save it to the buffer instead
                remainder = line
        self._extbytes = remainder

    def closed(self):
        self._logger.info("SSH command channel closed")
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
        self._logger = logging.getLogger(self.__class__.__name__)

        self.command = command
        self.user = user
        self.protocol = _CommandTransport
        self.finished = Deferred()

    def clientConnectionLost(self, connector, reason):
        self._logger.info("Client connection lost: %s, %s, %s", connector, reason, reason.type)
        if not self.finished.called:  # TODO: This could be prettier
            if reason.type is ConnectionDone:
                self.finished.callback(None)
            else:
                self.finished.errback(reason)


def runRemoteCMD(host, command):
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

    return factory.finished

#
# sshrunner.py ends here
