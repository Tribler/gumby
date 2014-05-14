#!/usr/bin/env python

import sys
from os import path, environ
from time import time
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main, buffer_online

from twisted.python.log import msg
from twisted.python.threadable import isInIOThread
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class DiscoveryClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from dispersy.discovery.community import DiscoveryCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = DiscoveryCommunity

        self.friends = set()
        self.friendhashes = {}
        self.friendiphashes = {}
        self.not_connected_friends = set()

        self.preferences = set()

        self.set_community_kwarg('max_prefs', 25)
        self.set_community_kwarg('max_tbs', 25)

        self.monitor_friends_lc = None
        self._prev_scenario_statistics = {}
        self._prev_scenario_debug = {}

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

    def start_dispersy(self, autoload_discovery=True):
        DispersyExperimentScriptClient.start_dispersy(self, autoload_discovery=False)

    def online(self):
        DispersyExperimentScriptClient.online(self)
        self._community.my_preferences = self.get_preferences

    def get_preferences(self):
        return list(self.preferences)

    @buffer_online
    def insert_my_key(self):
        pass

    def add_friend(self, peer_id):
        try:
            if peer_id != self.my_id:
                peer_id = int(peer_id)

                # if we don't get the ipport, then this peer isn't deployed to the das
                ipport = self.get_peer_ip_port_by_id(peer_id)
                key = self.get_private_keypair_by_id(peer_id)

                print >> sys.stderr, "add_friend", peer_id, ipport, bool(key)

                if ipport and key:
                    key = key.pub()
                    keyhash = self._crypto.key_to_hash(key)
                    keyhash_as_long = long(sha1(self._crypto.key_to_bin(key)).hexdigest(), 16)

                    self.preferences.add(sha1(str(peer_id)).digest())

                    self.friends.add(keyhash)
                    self.friendhashes[peer_id] = keyhash_as_long
                    self.friendiphashes[ipport] = keyhash_as_long

                    print >> sys.stderr, "friend added", len(self.friends)

                    if not self.monitor_friends_lc:
                        self.monitor_friends_lc = lc = LoopingCall(self.monitor_friends)
                        lc.start(5.0, now=True)

                elif ipport:
                    print >> sys.stderr, "Got ip/port, but not key?", peer_id
                else:
                    print >> sys.stderr, "No ip/port or key", peer_id
        except:
            from traceback import print_exc
            print_exc()

    @buffer_online
    def add_foaf(self, peer_id, his_friends):
        pass

    @buffer_online
    def send_post(self, peer_id, nr_messages=1):
        pass

    def connect_to_friends(self):
        pass

    def monitor_friends(self):
        connected_friends = 0
        for mid in self.friends:
            if self._community and self._community.is_taste_buddy_mid(mid):
                connected_friends += 1

        if self.friends:
            bootstrapped = connected_friends / float(len(self.friends))
        else:
            bootstrapped = 0

        self._prev_scenario_statistics = self.print_on_change("scenario-statistics", self._prev_scenario_statistics, {'bootstrapped': bootstrapped})
        if self._community:
            self._prev_scenario_debug = self.print_on_change("scenario-debug", self._prev_scenario_debug, {'nr_friends':len(self.friends) if self.friends else 0})

if __name__ == '__main__':
    DiscoveryClient.scenario_file = environ.get('SCENARIO_FILE', 'social.scenario')
    main(DiscoveryClient)

