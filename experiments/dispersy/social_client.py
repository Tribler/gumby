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
import sys
from os import path, environ
from time import time
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main, buffer_online

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class SocialClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesocial.community import PoliSocialCommunity
        from Tribler.community.privatesemantic.community import PSI_OVERLAP
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PoliSocialCommunity

        self.friends = set()
        self.not_connected_friends = set()
        self.foafs = set()
        self.not_connected_foafs = set()

        self.peercache = False
        self.nocache = False
        self.reconnect_to_friends = False
        self._mypref_db = None

        self.monitor_friends_lc = None
        self.prev_scenario_statistics = {}
        self.prev_scenario_debug = {}

        self.friendhashes = {}
        self.friendiphashes = {}
        self.foafiphashes = {}

        self.set_community_kwarg('integrate_with_tribler', False)
        self.set_community_kwarg('encryption', False)
        self.set_community_kwarg('max_prefs', 100)
        self.set_community_kwarg('max_fprefs', 100)
        self.set_community_kwarg('psi_mode', PSI_OVERLAP)
        self.set_community_kwarg('log_text', self.log_text)

    def registerCallbacks(self):
        self.scenario_runner.register(self.insert_my_key, 'insert_my_key')
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.add_foaf, 'add_foaf')
        self.scenario_runner.register(self.connect_to_friends, 'connect_to_friends')
        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.send_post, 'send_post')
        self.scenario_runner.register(self.set_cache, 'set_cache')

    def peertype(self, peertype):
        DispersyExperimentScriptClient.peertype(self, peertype)
        if peertype == "peercache":
            self.peercache = True

    def set_cache(self, cache):
        self.nocache = not self.str2bool(cache)

    def initializeCrypto(self):
        from Tribler.community.privatesemantic.crypto.elgamalcrypto import ElgamalCrypto, NoElgamalCrypto
        if environ.get('TRACKER_CRYPTO', 'ECCrypto') == 'ECCrypto':
            return ElgamalCrypto()

        self._logger.info('Turning off Crypto')
        return NoElgamalCrypto()

    def set_community_class(self, commtype):
        from Tribler.community.privatesocial.community import NoFSocialCommunity, PSocialCommunity, HSocialCommunity, PoliSocialCommunity
        if commtype == "nof":
            self.community_class = NoFSocialCommunity
        elif commtype == "p":
            self.community_class = PSocialCommunity
        elif commtype == "h":
            self.community_class = HSocialCommunity
        elif commtype == "poli":
            self.community_class = PoliSocialCommunity
        else:
            raise RuntimeError("undefined class type, %s" % commtype)

    def online(self):
        if self.peercache:
            yield 30.0

        # if we're peercache -> enable send_simi_reveal, else disable
        self.set_community_kwarg('send_simi_reveal', self.peercache)

        DispersyExperimentScriptClient.online(self, dont_empty=True)
        self._orig_create_msimilarity_request = self._community.create_msimilarity_request

        if self._mypref_db:
            self._community._mypref_db = self._mypref_db

        if self.reconnect_to_friends:
            self._community.connect_to_peercache(sys.maxint)

            # we're going to allow this peer to connect to its friends for 5.0 seconds, then empty the buffer
            yield 5.0
        else:
            # if not reconnect_to_friends, connect_to_friend hasn't been called, hence
            # we disable simi requests
            self._community.create_msimilarity_request = lambda destination: False
        self.empty_buffer()

    def offline(self):
        if self._community:
            self._mypref_db = self._community._mypref_db

        DispersyExperimentScriptClient.offline(self)

    @buffer_online
    def insert_my_key(self):
        key = self._crypto.key_from_private_bin(self.my_member_private_key)

        keyhash = long(sha1(self._crypto.key_to_bin(key.pub())).hexdigest(), 16)
        self._community._mypref_db.addMyPreference(keyhash, {})
        self._community._friend_db.add_my_key(key, keyhash)

    @buffer_online
    def add_friend(self, peer_id):
        if peer_id != self.my_id:
            peer_id = int(peer_id)

            # if we don't get the ipport, then this peer isn't deployed to the das
            ipport = self.get_peer_ip_port_by_id(peer_id)
            key = self.get_private_keypair_by_id(peer_id)

            if ipport and key:
                key = key.pub()
                keyhash = self._crypto.key_to_hash(key)
                keyhash_as_long = long(sha1(self._crypto.key_to_bin(key)).hexdigest(), 16)
                self._community._mypref_db.addMyPreference(keyhash_as_long, {})
                self._community._friend_db.add_friend(str(peer_id), key, keyhash_as_long)

                self.friends.add(keyhash)
                self.friendhashes[peer_id] = keyhash_as_long
                self.friendiphashes[ipport] = keyhash_as_long

                if not self.monitor_friends_lc:
                    self.monitor_friends_lc = lc = LoopingCall(self.monitor_friends)
                    lc.start(5.0, now=True)

            elif ipport:
                print >> sys.stderr, "Got ip/port, but not key?", peer_id

    @buffer_online
    def add_foaf(self, peer_id, his_friends):
        if peer_id != self.my_id:
            peer_id = int(peer_id)

            his_friends = [int(friend) for friend in his_friends[1:-1].split(",") if friend != self.my_id]

            # if we don't get the ipport, then this peer isn't deployed to the das
            ipport = self.get_peer_ip_port_by_id(peer_id)
            key = self.get_private_keypair_by_id(peer_id)

            if ipport:
                key = key.pub()
                keyhash = self._crypto.key_to_hash(key)
                self.foafs.add(keyhash)
                self.foafiphashes[ipport] = [self.friendhashes[peer_id] for peer_id in his_friends if peer_id in self.friendhashes]

                if not self.monitor_friends_lc:
                    self.monitor_friends_lc = lc = LoopingCall(self.monitor_friends)
                    lc.start(5.0, now=True)

    @buffer_online
    def send_post(self, peer_id, nr_messages=1):
        if peer_id != self.my_id:
            peer_id = int(peer_id)
            for _ in range(int(nr_messages)):
                msg = u"Hello peer %d" % peer_id
                self._community.create_text(msg, [str(peer_id), ])

    @buffer_online
    def connect_to_friends(self):
        friendsaddresses = self.friendiphashes.keys()
        foafsaddresses = self.foafiphashes.keys()

        if self.peercache:
            if self.nocache:
                friendsaddresses = []
                foafsaddresses = []
            else:
                friendsaddresses = sample(friendsaddresses, int(len(friendsaddresses) * 0.36))
                foafsaddresses = sample(foafsaddresses, int(len(foafsaddresses) * 0.36))

        my_hashes = [keyhash for _, keyhash in self._community._friend_db.get_my_keys()]
        for ipport in friendsaddresses:
            self._community._peercache.add_peer(my_hashes + [self.friendiphashes[ipport], ], *ipport)

        for ipport in foafsaddresses:
            self._community._peercache.add_peer(self.foafiphashes[ipport], *ipport)

        # use peercache to connect to friends
        self._community.connect_to_peercache(sys.maxint)

        # enable normal discovery of foafs
        self._community.create_msimilarity_request = self._orig_create_msimilarity_request

        self.reconnect_to_friends = True

    def log_text(self, key, sock_addr, **kwargs):
        kwargs['from_friend'] = sock_addr in self.friendiphashes
        kwargs['from_foaf'] = sock_addr in self.foafiphashes
        kwargs['sock_addr'] = sock_addr

        self.print_on_change(key, {}, kwargs)

    def monitor_friends(self):
        connected_friends = 0
        indirectly_connected_friends = 0
        for mid in self.friends:
            if self._community and self._community.is_taste_buddy_mid(mid):
                connected_friends += 1
            if self._community and self._community.is_overlapping_taste_buddy_mid(mid):
                indirectly_connected_friends += 1

        connected_foafs = 0
        for mid in self.foafs:
            if self._community and self._community.is_taste_buddy_mid(mid):
                connected_foafs += 1

        if self.friends:
            bootstrapped = connected_friends / float(len(self.friends))
            indirect_bootstrapped = indirectly_connected_friends / float(len(self.friends))
        else:
            bootstrapped = 0

        if self.foafs:
            bootstrapped_foafs = connected_foafs / float(len(self.foafs))
        else:
            bootstrapped_foafs = 0

        self.prev_scenario_statistics = self.print_on_change("scenario-statistics", self.prev_scenario_statistics, {'bootstrapped': bootstrapped, 'bootstrapped_foafs': bootstrapped_foafs, 'indirect_bootstrapped':indirect_bootstrapped})
        if self._community:
            self.prev_scenario_debug = self.print_on_change("scenario-debug", self.prev_scenario_debug, {'create_time_encryption':self._community.create_time_encryption, 'create_time_decryption':self._community.create_time_decryption, 'receive_time_encryption':self._community.receive_time_encryption})

if __name__ == '__main__':
    SocialClient.scenario_file = environ.get('SCENARIO_FILE', 'social.scenario')
    main(SocialClient)

#
# social_client.py ends here
