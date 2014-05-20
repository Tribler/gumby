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
        self.preferences = set()

        self.set_community_kwarg('max_prefs', sys.maxint)
        self.set_community_kwarg('max_tbs', 25)

        self.monitor_friends_lc = None
        self._prev_scenario_statistics = {}
        self._prev_scenario_debug = {}

    def registerCallbacks(self):
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.ignore_call, 'add_foaf')
        self.scenario_runner.register(self.ignore_call, 'connect_to_friends')
        self.scenario_runner.register(self.ignore_call, 'set_community_class')
        self.scenario_runner.register(self.ignore_call, 'send_post')
        self.scenario_runner.register(self.ignore_call, 'set_cache')
        self.scenario_runner.register(self.ignore_call, 'insert_my_key')


        #compatibility with privatesemantic scenario
        self.scenario_runner.register(self.download, 'download')
        self.scenario_runner.register(self.download, 'testset')
        self.scenario_runner.register(self.add_friend, 'taste_buddy')
        self.scenario_runner.register(self.ignore_call, 'connect_to_taste_buddies')
        self.scenario_runner.register(self.ignore_call, 'set_manual_connect')
        self.scenario_runner.register(self.ignore_call, 'set_random_connect')
        self.scenario_runner.register(self.ignore_call, 'set_bootstrap_percentage')
        self.scenario_runner.register(self.ignore_call, 'set_latejoin')
        self.scenario_runner.register(self.ignore_call, 'set_search_spacing')
        self.scenario_runner.register(self.ignore_call, 'set_do_search')
        self.scenario_runner.register(self.ignore_call, 'set_search_limit')
        self.scenario_runner.register(self.ignore_call, 'availability')
        self.scenario_runner.register(self.ignore_call, 'perform_searches')

    def start_dispersy(self, autoload_discovery=True):
        DispersyExperimentScriptClient.start_dispersy(self, autoload_discovery=False)

    def set_community_kwarg(self, key, value):
        pass

    def online(self):
        DispersyExperimentScriptClient.online(self)
        self._community.my_preferences = self.get_preferences

    def get_preferences(self):
        if self.preferences:
            return list(self.preferences)

        return list(self.friends) + [self._my_member.mid]

    def add_friend(self, peer_id, similarity=None):
        try:
            if peer_id != self.my_id:
                peer_id = int(peer_id)

                # if we don't get the ipport, then this peer isn't deployed to the das
                ipport = self.get_peer_ip_port_by_id(peer_id)
                key = self.get_private_keypair_by_id(peer_id)

                if ipport and key:
                    key = key.pub()
                    keyhash = self._crypto.key_to_hash(key)

                    self.friends.add(keyhash)

                    print >> sys.stderr, "friend added", peer_id, keyhash.encode('HEX'), "now have %d friends" % len(self.friends)

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

    def download(self, infohash):
        self.preferences.add(sha1(str(infohash)).digest())

    def ignore_call(self, *args):
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

