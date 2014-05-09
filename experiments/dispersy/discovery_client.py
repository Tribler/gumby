#!/usr/bin/env python

import sys
from os import path, environ
from time import time
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main, buffer_online

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class DiscoveryClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from dispersy.discovery.community import DiscoveryCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = DiscoveryCommunity

        self.friends = set()
        self.not_connected_friends = set()

        self.preferences = set()

        self.set_community_kwarg('max_prefs', 10)
        self.set_community_kwarg('max_tbs', 25)
        self.set_community_kwarg('log_text', self.log_text)

    def registerCallbacks(self):
        self.scenario_runner.register(self.insert_my_key, 'insert_my_key')
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.add_foaf, 'add_foaf')
        self.scenario_runner.register(self.connect_to_friends, 'connect_to_friends')
        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.send_post, 'send_post')
        self.scenario_runner.register(self.set_cache, 'set_cache')

    def set_cache(self, cache):
        pass

    def set_community_class(self, commtype):
        from dispersy.discovery.community import DiscoveryCommunity
        if commtype == "disc":
            self.community_class = DiscoveryCommunity
        else:
            raise RuntimeError("undefined class type, %s" % commtype)

    @call_on_dispersy_thread
    def online(self):
        DispersyExperimentScriptClient.online(self)
        self._community.my_preferences = self.get_preferences

    def get_preferences(self):
        return list(self.preferences)

    @buffer_online
    def insert_my_key(self):
        pass

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

                self.preferences.add(sha1(peer_id).digest())

                self.friends.add(keyhash)
                self.friendhashes[peer_id] = keyhash_as_long
                self.friendiphashes[ipport] = keyhash_as_long

                self._dispersy.callback.persistent_register(u"monitor_friends", self.monitor_friends)

            elif ipport:
                print >> sys.stderr, "Got ip/port, but not key?", peer_id

    @buffer_online
    def add_foaf(self, peer_id, his_friends):
        pass

    @buffer_online
    def send_post(self, peer_id, nr_messages=1):
        pass

    @buffer_online
    def connect_to_friends(self):
        friendsaddresses = self.friendiphashes.keys()

        if self.peercache:
            if self.nocache:
                friendsaddresses = []
            else:
                friendsaddresses = sample(friendsaddresses, int(len(friendsaddresses) * 0.36))

        my_hashes = [keyhash for _, keyhash in self._community._friend_db.get_my_keys()]
        for ipport in friendsaddresses:
            self._community._peercache.add_peer(my_hashes + [self.friendiphashes[ipport], ], *ipport)

        self._community.connect_to_peercache(sys.maxint)
        self.reconnect_to_friends = True

    def log_text(self, key, sock_addr, **kwargs):
        kwargs['from_friend'] = sock_addr in self.friendiphashes
        kwargs['from_foaf'] = False
        kwargs['sock_addr'] = sock_addr

        self.print_on_change(key, {}, kwargs)

    def monitor_friends(self):
        prev_scenario_statistics = {}
        prev_scenario_debug = {}

        while True:
            connected_friends = 0
            indirectly_connected_friends = 0
            for mid in self.friends:
                if self._community and self._community.is_taste_buddy_mid(mid):
                    connected_friends += 1
                if self._community and (self._community.is_taste_buddy_mid(mid) or any([tb.does_overlap(long(hexlify(mid), 16)) for tb in self._community.yield_taste_buddies()])):
                    indirectly_connected_friends += 1

            if self.friends:
                bootstrapped = connected_friends / float(len(self.friends))
                indirect_bootstrapped = indirectly_connected_friends / float(len(self.friends))
            else:
                bootstrapped = 0

            prev_scenario_statistics = self.print_on_change("scenario-statistics", prev_scenario_statistics, {'bootstrapped': bootstrapped, 'bootstrapped_foafs': 0, 'indirect_bootstrapped':indirect_bootstrapped})
            if self._community:
                prev_scenario_debug = self.print_on_change("scenario-debug", prev_scenario_debug, {'create_time_encryption':0, 'create_time_decryption':0, 'receive_time_encryption':0})
            yield 5.0

if __name__ == '__main__':
    DiscoveryClient.scenario_file = environ.get('SCENARIO_FILE', 'social.scenario')
    main(DiscoveryClient)

