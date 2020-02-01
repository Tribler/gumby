#!/usr/bin/env python3
# config.py ---
#
# Filename: config.py
# Description:
# Author: Elric Milon, Vlad Dumitrescu
# Maintainer:
# Created: Mon Jul  1 18:15:27 2013 (+0200)

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
from getpass import getuser
from hashlib import md5
from time import time

from gumby.line_receiver import LineReceiver


class _ConfigClientProtocol(LineReceiver):

    """
    Protocol messages:
        1) send TIME - current time at this peer, so they all start the
                       experiment at the same time
        2) recv MYCONFIG - configuration params for this peer: myid, ip:port,
                           start_timestamp
        3) recv FULLCONFIG - data about all the other peers that reported
        4) send LOGGING - TODO
    """

    def __init__(self):
        self.state = None
        self.config = None

    def connectionMade(self):
        self.send_line(b"TIME " + str(time()))

        # goto recv MYCONFIG
        self.state = 1

    def line_received(self, data):
        if self.state == 1:
            data = data.strip()
            id, ip, port, start_timestamp = data.split()
            self.config = {
                "my": {
                    "id": id,
                    "ip": ip,
                    "port": port,
                    "start_timestamp": start_timestamp
                },
                "others": []
            }

            # goto recv FULLCONFIG
            self.state = 2
        elif self.state == 2:
            # receiving full configuration until "END"
            if data != "END":
                ip, port = data.split()
                self.config["others"].append({
                    "ip": ip,
                    "port": port
                })
            else:
                self.factory.onConfigReceived.callback(self.config)

                # TODO: goto send LOGGING
                # self.state = 3
        # elif self.state == 3:


def get_config_server_endpoint():
    """
    Get config server's IP/hostname and port from the environment. If specific
    hostname is not given, use the first head node. If port is not given,
    generate one based on the current user.

    TODO: These should always exist. The runner can set them after executing
          config_server_cmd.
    """
    if "CONFIG_SERVER_HOST" in os.environ:
        host = os.environ["CONFIG_SERVER_HOST"]
    else:
        host = eval(os.environ["HEAD_NODES"])[0].split("@")[1]

    if "CONFIG_SERVER_PORT" in os.environ:
        port = os.environ["CONFIG_SERVER_PORT"]
    else:
        # determine port based on the process owner's username
        md5sum = md5()
        md5sum.update(getuser())
        port = int(md5sum.hexdigest()[-16:], 16) % 20000 + 15000

    return (host, port)

#
# config.py ends here
