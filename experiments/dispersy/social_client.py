#!/usr/bin/env python
# social_client.py ---
#
# Filename: social_client.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Mon Oct 28 14:10:00 2013 (+0200)

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

from os import path
from random import choice
from string import letters
from sys import path as pythonpath

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class SocialClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesocial.community import PSearchCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PSearchCommunity

        self.friends = set()
        self.not_connected_friends = set()

        self.set_community_kwarg('integrate_with_tribler', False)

    def start_dispersy(self):
        DispersyExperimentScriptClient.start_dispersy(self)
        self.community_args = (self._my_member,)

    def registerCallbacks(self):
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.connect_to_friends, 'connect_to_friends')

    def set_peer_type(self, peertype):
        DispersyExperimentScriptClient.set_peer_type(self, peertype)
        if peertype == "late join":
            self.latejoin = True

    def online(self):
        DispersyExperimentScriptClient.online(self)
        self._dispersy.callback.register(self.monitor_friends)

    def add_friend(self, peer_id, key):
        from Tribler.community.privatesemantic.rsa import bytes_to_key

        peer_id = int(peer_id)
        key = key.replace("_", " ")
        key = bytes_to_key(key)

        self._community._db.set_key(peer_id, key)

        ip, port = self.get_peer_ip_port(peer_id)

        self.friends.add((ip, port))
        self.not_connected_friends.add((ip, port))

    def connect_to_friends(self):
        for ipport in self.friends:
            self._dispersy.callback.register(self.connect_to_friend, args=(ipport,))

    def connect_to_friend(self, sock_addr):
        from Tribler.dispersy.dispersy import IntroductionRequestCache

        candidate = self._community.get_candidate(sock_addr, replace=False)
        if not candidate:
            candidate = self._community.create_candidate(sock_addr, False, sock_addr, sock_addr, u"unknown")

        while not self._community.is_taste_buddy(candidate):
            msg("sending introduction request to %s" % str(candidate))
            self._manual_create_introduction_request(candidate, True)

            yield IntroductionRequestCache.timeout_delay + IntroductionRequestCache.cleanup_delay

    def monitor_friends(self):
        prev_scenario_statistics = {}
        prev_scenario_debug = {}

        while True:
            for sock_addr in self.friends:
                if self._community.is_taste_buddy_sock(sock_addr):
                    if sock_addr in self.not_connected_friends:
                        self.not_connected_friends.remove(sock_addr)
                else:
                    self.not_connected_friends.add(sock_addr)

            if len(self.friends):
                connected_friends = len(self.friends) - len(self.not_connected_friends)
                bootstrapped = connected_friends / float(len(self.friends))
            else:
                bootstrapped = 0

            prev_scenario_statistics = self.print_on_change("scenario-statistics", prev_scenario_statistics, {'bootstrapped': bootstrapped})
            prev_scenario_debug = self.print_on_change("scenario-debug", prev_scenario_debug, {'not_connected':list(self.not_connected_friends)})
            yield 5.0

if __name__ == '__main__':
    SocialClient.scenario_file = "social.scenario"
    main(SocialClient)

#
# social_client.py ends here
