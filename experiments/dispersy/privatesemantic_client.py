#!/usr/bin/env python
# Author: Niels Zeilemaker

import sys

from os import path
from random import choice, randint, sample, random
from string import letters
from sys import path as pythonpath
from time import time, sleep
from collections import defaultdict
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

DEBUG = False

class PrivateSemanticClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesemantic.test import PoliFSemanticCommunity

        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PoliFSemanticCommunity

        self.manual_connect = False
        self.random_connect = False
        self.bootstrap_percentage = 1.0
        self.late_join = 0

        self.taste_buddies = {}
        self.not_connected_taste_buddies = set()

        self.log_statistics_lc = None
        self.prev_scenario_statistics = {}
        self.prev_scenario_debug = {}

        self.community_kwargs['integrate_with_tribler'] = False

    def registerCallbacks(self):
        self.scenario_runner.register(self.download, 'download')
        self.scenario_runner.register(self.testset, 'testset')
        self.scenario_runner.register(self.taste_buddy, 'taste_buddy')
        self.scenario_runner.register(self.connect_to_taste_buddies, 'connect_to_taste_buddies')

        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.set_manual_connect, 'set_manual_connect')
        self.scenario_runner.register(self.set_random_connect, 'set_random_connect')
        self.scenario_runner.register(self.set_bootstrap_percentage, 'set_bootstrap_percentage')
        self.scenario_runner.register(self.set_latejoin, 'set_latejoin')

    def download(self, infohash):
        infohash = long(sha1(str(infohash)).hexdigest(), 16)
        self._community._mypref_db.addMyPreference(infohash, {})

    def testset(self, infohash):
        infohash = long(sha1(str(infohash)).hexdigest(), 16)
        self._community._mypref_db.addTestPreference(infohash)

    def taste_buddy(self, peer_id, similarity):
        peer_id = int(peer_id)
        similarity = float(similarity)
        ipport = self.get_peer_ip_port_by_id(peer_id)

        if ipport:
            self.taste_buddies[ipport] = similarity
            self.not_connected_taste_buddies.add(ipport)

            similarities = self.taste_buddies.keys()
            similarities.sort(reverse=True, cmp=lambda a, b: cmp(self.taste_buddies[a], self.taste_buddies[b]))

            for ipport in similarities[10:]:
                if self.taste_buddies[similarities[9]] > self.taste_buddies[ipport]:
                    del self.taste_buddies[ipport]
                    self.not_connected_taste_buddies.discard(ipport)

            if DEBUG:
                print >> sys.stderr, "tbs:", self.taste_buddies.items()

    def set_community_class(self, commtype):
        from Tribler.community.privatesemantic.test import NoFSemanticCommunity, HFSemanticCommunity, PFSemanticCommunity, PoliFSemanticCommunity

        if commtype == 'nof':
            self.community_class = NoFSemanticCommunity
        elif commtype == 'hsem':
            self.community_class = HFSemanticCommunity
        elif commtype == 'polisem':
            self.community_class = PoliFSemanticCommunity
        else:
            self.community_class = PFSemanticCommunity

    def set_manual_connect(self, manual_connect):
        self.manual_connect = self.str2bool(manual_connect)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: manual_connect is now", self.manual_connect

    def set_random_connect(self, random_connect):
        self.random_connect = self.str2bool(random_connect)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: random_connect is now", self.random_connect

    def set_bootstrap_percentage(self, bootstrap_percentage):
        self.bootstrap_percentage = float(bootstrap_percentage)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: bootstrap_percentage is now", self.bootstrap_percentage

    def set_latejoin(self, latejoin):
        self.late_join = int(latejoin)
        if int(self.my_id) <= self.late_join:
            self.peertype('latejoining')
        else:
            self.peertype('bootstrapped')

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: late_join is now", self.late_join

    def set_do_search(self, do_search):
        self.do_search = int(do_search)
        if int(self.my_id) <= self.do_search:
            self.peertype('searching')
        else:
            self.peertype('idle')

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: do_search is now", self.do_search

    def set_search_limit(self, search_limit):
        self.search_limit = int(search_limit)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: search_limit is now", self.search_limit

    def set_search_spacing(self, search_spacing):
        self.search_spacing = float(search_spacing)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: search_spacing is now", self.search_spacing

    def set_community_kwarg(self, key, value):
        if key in ['max_prefs', 'max_fprefs']:
            value = int(value)
        elif key in ['encryption', 'send_simi_reveal']:
            value = self.str2bool(value)
        else:
            return

        DispersyExperimentScriptClient.set_community_kwarg(self, key, value)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: community_kwargs are now", self.community_kwargs

    def online(self):
        sleep(random() * 5.0)

        DispersyExperimentScriptClient.online(self)

        # disable msimilarity requests
        self._orig_create_msimilarity_request = self._community.create_msimilarity_request
        self._community.create_msimilarity_request = lambda destination: False

    def connect_to_taste_buddies(self):
        if not self.log_statistics_lc:
            self.log_statistics_lc = lc = LoopingCall(self.log_statistics)
            lc.start(5.0, now=True)

        if int(self.my_id) > self.late_join:
            nr_to_connect = int(10 * self.bootstrap_percentage)
            print >> sys.stderr, "will connect to", nr_to_connect

            if self.random_connect:
                taste_addresses = [self.get_peer_ip_port_by_id(peer_id) for peer_id in sample(self.get_peers(), nr_to_connect)]
                for ipport in taste_addresses:
                    self._community._peercache.add_peer(0, *ipport)
            else:
                taste_addresses = self.taste_buddies.keys()
                for ipport in taste_addresses:
                    self._community._peercache.add_peer(self.taste_buddies.get(ipport, 0), *ipport)

            self._community.connect_to_peercache(nr_to_connect)

        # enable normal discovery of foafs
        self._community.create_msimilarity_request = self._orig_create_msimilarity_request

    def log_statistics(self):
        if DEBUG:
            tsock_addrs = [candidate.sock_addr for candidate in self._community.yield_taste_buddies()]
            msock_addrs = self.taste_buddies.keys()
            print >> sys.stderr, "Comparing", tsock_addrs, msock_addrs

        for sock_addr in self.taste_buddies.keys():
            if self._community.is_taste_buddy_sock(sock_addr):
                if sock_addr in self.not_connected_taste_buddies:
                    self.not_connected_taste_buddies.remove(sock_addr)
            else:
                self.not_connected_taste_buddies.add(sock_addr)

        connected_friends = min(len(self.taste_buddies) - len(self.not_connected_taste_buddies), 10)
        max_connected = min(int(10 * self.bootstrap_percentage), len(self.taste_buddies))
        if max_connected:
            bootstrapped = connected_friends / float(max_connected)
        else:
            bootstrapped = 0

        self.print_on_change("scenario-statistics", self.prev_scenario_statistics, {'bootstrapped':bootstrapped})
        self.print_on_change("scenario-debug", self.prev_scenario_debug, {'not_connected':list(self.not_connected_taste_buddies), 'create_time_encryption':self._community.create_time_encryption, 'create_time_decryption':self._community.create_time_decryption, 'receive_time_encryption':self._community.receive_time_encryption, 'send_packet_size':self._community.send_packet_size, 'reply_packet_size':self._community.reply_packet_size, 'forward_packet_size':self._community.forward_packet_size})

if __name__ == '__main__':
    PrivateSemanticClient.scenario_file = 'privatesemantic_1000.scenario'
    main(PrivateSemanticClient)

#
# privatesemantic_client.py ends here
