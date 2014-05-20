#!/usr/bin/env python
# privatesearch_client.py ---
#
# Filename: privatesearch_client.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Mon Dec 2 18:29:33 2013 (+0200)

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

from os import path
from random import choice, randint, sample
from string import letters
from sys import path as pythonpath
from time import time
from collections import defaultdict
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

DEBUG = False

class PrivateSearchClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesearch.community import PoliSearchCommunity

        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PoliSearchCommunity

        self.manual_connect = False
        self.random_connect = False
        self.bootstrap_percentage = 1.0
        self.late_join = 0
        self.do_search = 1000
        self.search_limit = sys.maxint
        self.search_spacing = 15.0

        self.did_reply = set()
        self.test_set = set()
        self.test_reply = defaultdict(list)

        self.taste_buddies = {}
        self.not_connected_taste_buddies = set()
        self.file_availability = defaultdict(list)

        self.nr_search = 0

        self.log_statistics_lc = None
        self.prev_scenario_statistics = {}
        self.prev_scenario_debug = {}

        self.community_kwargs['integrate_with_tribler'] = False
        self.community_kwargs['log_searches'] = self.log_searches

    def registerCallbacks(self):
        self.scenario_runner.register(self.download, 'download')
        self.scenario_runner.register(self.testset, 'testset')
        self.scenario_runner.register(self.availability, 'availability')
        self.scenario_runner.register(self.taste_buddy, 'taste_buddy')
        self.scenario_runner.register(self.perform_searches, 'perform_searches')
        self.scenario_runner.register(self.connect_to_taste_buddies, 'connect_to_taste_buddies')

        self.scenario_runner.register(self.set_community_class, 'set_community_class')
        self.scenario_runner.register(self.set_manual_connect, 'set_manual_connect')
        self.scenario_runner.register(self.set_random_connect, 'set_random_connect')
        self.scenario_runner.register(self.set_bootstrap_percentage, 'set_bootstrap_percentage')
        self.scenario_runner.register(self.set_latejoin, 'set_latejoin')
        self.scenario_runner.register(self.set_do_search, 'set_do_search')
        self.scenario_runner.register(self.set_search_limit, 'set_search_limit')
        self.scenario_runner.register(self.set_search_spacing, 'set_search_spacing')

    def download(self, infohash):
        infohash_str = infohash + " "* (20 - len(infohash))
        infohash = long(sha1(str(infohash)).hexdigest(), 16)

        self._community._mypref_db.addMyPreference(infohash, {})
        self._community._torrent_db.addTorrent(infohash_str, True)

    def testset(self, infohash):
        infohash_str = infohash + " "* (20 - len(infohash))
        infohash = long(sha1(str(infohash)).hexdigest(), 16)

        self._community._mypref_db.addTestPreference(infohash)
        self._community._torrent_db.addTorrent(infohash_str, False)
        self.test_set.add(infohash_str)

    def availability(self, infohash, peers):
        infohash_str = infohash + " "* (20 - len(infohash))

        peers = [peer for peer in peers.split(',') if peer != str(self.my_id) and self.get_peer_ip_port_by_id(peer)]
        self.file_availability[infohash_str] = peers

    def taste_buddy(self, peer_id, similarity):
        peer_id = int(peer_id)
        similarity = float(similarity)
        ipport = self.get_peer_ip_port_by_id(peer_id)

        if ipport:
            self.taste_buddies[ipport] = similarity
            self.not_connected_taste_buddies.add(ipport)

    def set_community_class(self, commtype):
        from Tribler.community.privatesearch.community import SearchCommunity, PSearchCommunity, HSearchCommunity, PoliSearchCommunity
        from Tribler.community.privatesearch.oneswarm.community import PoliOneSwarmCommunity

        if commtype == 'search':
            self.community_class = SearchCommunity
        elif commtype == 'hsearch':
            self.community_class = HSearchCommunity
        elif commtype == 'polisearch':
            self.community_class = PoliSearchCommunity
        elif commtype == 'oneswarm':
            self.community_class = PoliOneSwarmCommunity
        else:
            self.community_class = PSearchCommunity

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
        from Tribler.community.privatesearch.oneswarm.community import PoliOneSwarmCommunity

        if key == 'use_megacache':
            value = self.str2bool(value)

        elif self.community_class != PoliOneSwarmCommunity:
            if key in ['ttl', 'neighbors', 'fneighbors']:
                value = self.str2tuple(value)
            elif key in ['max_prefs', 'max_fprefs']:
                value = int(value)
            elif key == 'prob':
                value = float(value)
            elif key == 'encryption':
                value = self.str2bool(value)
            else:
                return

        elif key == 'cancel_after':
            value = self.str2tuple(value)
        else:
            return

        DispersyExperimentScriptClient.set_community_kwarg(self, key, value)

        if DEBUG:
            print >> sys.stderr, "PrivateSearchClient: community_kwargs are now", self.community_kwargs

    def online(self):
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

    def perform_searches(self):
        if int(self.my_id) <= self.do_search:
            if not self.log_statistics_lc:
                self.log_statistics_lc = lc = LoopingCall(self.log_statistics)
                lc.start(5.0, now=True)

            # add small initial delay, to load balance requests
            yield float(int(self.my_id) % self.search_spacing)

            while True:
                self.nr_search += 1

                # clear local test_reply dict + force remove test_set from megacache
                self.test_reply.clear()
                for infohash in self.test_set:
                    self._community._torrent_db.deleteTorrent(infohash)

                for infohash in self.test_set:
                    candidates, local_results, _ = self._community.create_search([unicode(infohash)], self.log_search_response)
                    candidates = map(str, candidates)

                    if local_results:
                        self.log_search_response([unicode(infohash)], local_results, None)

                    yield self.search_spacing

                if self.nr_search <= self.search_limit:
                    yield 300.0
                else:
                    break

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

        connected_friends = len(self.taste_buddies) - len(self.not_connected_taste_buddies)
        max_connected = min(int(10 * self.bootstrap_percentage), len(self.taste_buddies))
        if max_connected:
            bootstrapped = connected_friends / float(max_connected)
        else:
            bootstrapped = 0

        recall = len(self.test_reply) / float(len(self.test_set))

        paths_found = sum(len(paths) for paths in self.test_reply.itervalues())
        sources_found = 0
        for infohash, peers in self.test_reply.iteritems():
            print >> sys.stderr, "Received", infohash, "from", peers
            sources_found += sum(peer in self.file_availability[infohash] for peer in set(peers))

        unique_sources = float(sum([len(self.file_availability[infohash]) for infohash in self.test_reply.iterkeys()]))
        if unique_sources:
            sources_found = sources_found / unique_sources
            paths_found = paths_found / unique_sources

        self.print_on_change("scenario-statistics", self.prev_scenario_statistics, {'bootstrapped':bootstrapped, 'recall':recall, 'nr_search_':self.nr_search, 'paths_found':paths_found, 'sources_found':sources_found})
        self.print_on_change("scenario-debug", self.prev_scenario_debug, {'not_connected':list(self.not_connected_taste_buddies), 'search_forward':self._community.search_forward, 'search_forward_success':self._community.search_forward_success, 'search_forward_timeout':self._community.search_forward_timeout, 'search_endpoint':self._community.search_endpoint, 'search_cycle_detected':self._community.search_cycle_detected, 'search_no_candidates_remain':self._community.search_no_candidates_remain, 'search_megacachesize':self._community.search_megacachesize, 'create_time_encryption':self._community.create_time_encryption, 'create_time_decryption':self._community.create_time_decryption, 'receive_time_encryption':self._community.receive_time_encryption, 'search_timeout':self._community.search_timeout, 'send_packet_size':self._community.send_packet_size, 'reply_packet_size':self._community.reply_packet_size, 'forward_packet_size':self._community.forward_packet_size})

    def log_searches(self, key, **kwargs):
        self.print_on_change(key, {}, kwargs)

    def log_search_response(self, keywords, results, candidate):
        for result in results:
            if result[0] in self.test_set:
                ip, port = result[1].split()
                peer = self.get_peer_id(ip, port)
                self.test_reply[result[0]].append(peer)

        recall = len(self.test_reply) / float(len(self.test_set))
        paths_found = sum(len(paths) for paths in self.test_reply.itervalues())
        sources_found = 0
        for infohash, peers in self.test_reply.iteritems():
            sources_found += sum(peer in self.file_availability[infohash] for peer in set(peers))

        unique_sources = float(sum([len(self.file_availability[infohash]) for infohash in self.test_reply.iterkeys()]))
        if unique_sources:
            sources_found = sources_found / unique_sources
            paths_found = paths_found / unique_sources

        from Tribler.dispersy.tool.lencoder import log
        if results:
            log("dispersy.log", "results", recall=recall, paths_found=paths_found, sources_found=sources_found, keywords=keywords, candidate=str(candidate), results=results, unique_sources=unique_sources)
        else:
            log("dispersy.log", "no results", recall=recall, paths_found=paths_found, sources_found=sources_found, keywords=keywords, candidate=str(candidate), unique_sources=unique_sources)

if __name__ == '__main__':
    PrivateSearchClient.scenario_file = 'privatesearch_1000.scenario'
    main(PrivateSearchClient)

#
# privatesearch_client.py ends here
