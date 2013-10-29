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
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class SocialClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesocial.community import PSocialCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PSocialCommunity

        self.friends = set()
        self.not_connected_friends = set()

        self.peercache = False

        self.set_community_kwarg('integrate_with_tribler', False)
        self.set_community_kwarg('encryption', False)
        self.set_community_kwarg('max_prefs', 100)
        self.set_community_kwarg('max_fprefs', 100)

    def start_dispersy(self):
        DispersyExperimentScriptClient.start_dispersy(self)
        self.community_args = (self._my_member,)

    def registerCallbacks(self):
        self.scenario_runner.register(self.my_key, 'my_key')
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.connect_to_friends, 'connect_to_friends')

    def peertype(self, peertype):
        DispersyExperimentScriptClient.peertype(self, peertype)
        if peertype == "peercache":
            self.peercache = True

    @call_on_dispersy_thread
    def online(self):
        DispersyExperimentScriptClient.online(self)

        self._manual_create_introduction_request = self._community.create_introduction_request
        self._community.create_introduction_request = lambda destination, allow_sync: self._manual_create_introduction_request(destination, False)

    @call_on_dispersy_thread
    def my_key(self, key):
        from Tribler.community.privatesemantic.rsa import bytes_to_key

        keyhash = long(sha1(str(key)).hexdigest(), 16)
        self._community._mypref_db.addMyPreference(keyhash, {})

        key = key.replace("_", " ")
        key = bytes_to_key(key)
        self._community._friend_db.set_my_key(key)

    @call_on_dispersy_thread
    def add_friend(self, peer_id, key):
        from Tribler.community.privatesemantic.rsa import bytes_to_key

        keyhash = long(sha1(str(key)).hexdigest(), 16)
        self._community._mypref_db.addMyPreference(keyhash, {})

        peer_id = int(peer_id)

        key = key.replace("_", " ")
        key = bytes_to_key(key)
        self._community._friend_db.set_key(peer_id, key)

        ip, port = self.get_peer_ip_port(peer_id)

        self.friends.add((ip, port))
        self.not_connected_friends.add((ip, port))

        self._dispersy.callback.persistent_register(u"monitor_friends", self.monitor_friends)

    @call_on_dispersy_thread
    def connect_to_friends(self):
        if self.peercache:
            addresses = sample(self.friends, len(self.friends) * 0.36)
        else:
            addresses = self.friends

        for ipport in addresses:
            self._dispersy.callback.register(self.connect_to_friend, args=(ipport,))

        # enable normal discovery of foafs
        self._community.create_introduction_request = self._manual_create_introduction_request

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

            if self.friends:
                connected_friends = len(self.friends) - len(self.not_connected_friends)
                bootstrapped = connected_friends / float(len(self.friends))
            else:
                bootstrapped = 0

            connected_foafs = max(0, len(list(self._community.yield_taste_buddies())) - len(self.friends))

            prev_scenario_statistics = self.print_on_change("scenario-statistics", prev_scenario_statistics, {'bootstrapped': bootstrapped, 'connected_foafs': connected_foafs})
            prev_scenario_debug = self.print_on_change("scenario-debug", prev_scenario_debug, {'not_connected':list(self.not_connected_friends)})
            yield 5.0

if __name__ == '__main__':
    SocialClient.scenario_file = "social.scenario"
    main(SocialClient)

#
# social_client.py ends here
