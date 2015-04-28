#!/usr/bin/env python
# dispersyclient.py ---
#
# Filename: dispersyclient.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Sep 18 17:29:33 2013 (+0200)

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

import base64
import json
import logging
from collections import Iterable, defaultdict
from os import chdir, environ, getpid, makedirs, path, symlink
from random import random
from sys import exit, stderr, stdout
from time import time
from traceback import print_exc

from gumby.log import setupLogging
from gumby.scenario import ScenarioRunner
from gumby.sync import ExperimentClient, ExperimentClientFactory

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet.threads import deferToThread


def buffer_online(func):
    def helper(*args, **kargs):
        args[0].buffer_call(func, args, kargs)

    helper.__name__ = func.__name__
    return helper

class DispersyExperimentScriptClient(ExperimentClient):
    scenario_file = None

    def __init__(self, vars):
        ExperimentClient.__init__(self, vars)
        self._dispersy = None
        self._community = None
        self._database_file = u"dispersy.db"
        self._dispersy_exit_status = None
        self._is_joined = False
        self._strict = True
        self.community_args = []
        self.community_kwargs = {}
        self._stats_file = None
        self._online_buffer = []

        self._crypto = self.initializeCrypto()
        self.generateMyMember()
        self.vars['private_keypair'] = base64.encodestring(self.my_member_private_key)

    def onVarsSend(self):
        scenario_file_path = path.join(environ['EXPERIMENT_DIR'], self.scenario_file)
        self.scenario_runner = ScenarioRunner(scenario_file_path)

        t1 = time()
        self.scenario_runner._read_scenario(scenario_file_path)
        self._logger.debug('Took %.2f to read scenario file', time() - t1)

    def onIdReceived(self):
        self._logger.debug('Got ID %s assigned', self.my_id)
        self.scenario_runner.set_peernumber(int(self.my_id))
        # TODO(emilon): Auto-register this stuff
        self.scenario_runner.register(self.echo)
        self.scenario_runner.register(self.online)
        self.scenario_runner.register(self.offline)
        self.scenario_runner.register(self.churn)
        self.scenario_runner.register(self.churn, 'churn_pattern')
        self.scenario_runner.register(self.set_community_kwarg)
        self.scenario_runner.register(self.set_database_file)
        self.scenario_runner.register(self.use_memory_database)
        self.scenario_runner.register(self.set_ignore_exceptions)
        self.scenario_runner.register(self.start_dispersy)
        self.scenario_runner.register(self.stop_dispersy)
        self.scenario_runner.register(self.stop)
        self.scenario_runner.register(self.set_master_member)
        self.scenario_runner.register(self.reset_dispersy_statistics, 'reset_dispersy_statistics')
        self.scenario_runner.register(self.annotate)
        self.scenario_runner.register(self.peertype)

        self.registerCallbacks()

        t1 = time()
        self.scenario_runner.parse_file()
        self._logger.debug('Took %.2f to parse scenario file' , time() - t1)

    def startExperiment(self):
        self._logger.debug("Starting dispersy scenario experiment")

        # TODO(emilon): Move this to the right place
        # TODO(emilon): Do we want to have the .dbs in the output dirs or should they be dumped to /tmp?
        my_dir = path.join(environ['OUTPUT_DIR'], self.my_id)
        makedirs(my_dir)
        chdir(my_dir)
        self._stats_file = open("statistics.log", 'w')

        # TODO(emilon): Fix me or kill me
        try:
            bootstrap_fn = path.join(environ['PROJECT_DIR'], 'tribler', 'bootstraptribler.txt')
            if not path.exists(bootstrap_fn):
                bootstrap_fn = path.join(environ['PROJECT_DIR'], 'bootstraptribler.txt')
            symlink(bootstrap_fn, 'bootstraptribler.txt')
        except OSError:
            pass

        self.scenario_runner.run()

    def registerCallbacks(self):
        pass

    def initializeCrypto(self):
        try:
            from Tribler.dispersy.crypto import ECCrypto, NoCrypto
        except:
            from dispersy.crypto import ECCrypto, NoCrypto

        if environ.get('TRACKER_CRYPTO', 'ECCrypto') == 'ECCrypto':
            self._logger.debug('Turning on ECCrypto')
            return ECCrypto()
        self._logger.debug('Turning off Crypto')
        return NoCrypto()

    @property
    def my_member_key_curve(self):
        # low (NID_sect233k1) isn't actually that low, switching to 160bits as this is comparable to rsa 1024
        # http://www.nsa.gov/business/programs/elliptic_curve.shtml
        # speed difference when signing/verifying 100 items
        # NID_sect233k1 signing took 0.171 verify took 0.35 totals 0.521
        # NID_secp160k1 signing took 0.04 verify took 0.04 totals 0.08
        return u"NID_secp160k1"

    def generateMyMember(self):
        ec = self._crypto.generate_key(self.my_member_key_curve)
        self.my_member_key = self._crypto.key_to_bin(ec.pub())
        self.my_member_private_key = self._crypto.key_to_bin(ec)
    #
    # Actions
    #

    def echo(self, *argv):
        self._logger.debug("%s ECHO %s", self.my_id, ' '.join(argv))

    def set_community_args(self, args):
        """
        Example: '1292333014,12923340000'
        """
        self.community_args = args.split(',')

    def set_community_kwargs(self, kwargs):
        """
        Example: 'startingtimestamp=1292333014,endingtimestamp=12923340000'
        """
        for karg in kwargs.split(","):
            if "=" in karg:
                key, value = karg.split("=", 1)
                self.community_kwargs[key.strip()] = value.strip()

    def set_community_kwarg(self, key, value):
        self.community_kwargs[key] = value

    def set_database_file(self, filename):
        self._database_file = unicode(filename)

    def use_memory_database(self):
        self._database_file = u':memory:'

    def set_ignore_exceptions(self, boolean):
        self._strict = not self.str2bool(boolean)

    def start_dispersy(self, autoload_discovery=True):
        self._logger.debug("Starting dispersy")
        # We need to import the stuff _AFTER_ configuring the logging stuff.
        try:
            from Tribler.dispersy.dispersy import Dispersy
            from Tribler.dispersy.endpoint import StandaloneEndpoint
            from Tribler.dispersy.util import unhandled_error_observer
        except:
            from dispersy.dispersy import Dispersy
            from dispersy.endpoint import StandaloneEndpoint
            from dispersy.util import unhandled_error_observer

        self._dispersy = Dispersy(StandaloneEndpoint(int(self.my_id) + 12000, '0.0.0.0'), u'.', self._database_file, self._crypto)
        self._dispersy.statistics.enable_debug_statistics(True)

        self.original_on_incoming_packets = self._dispersy.on_incoming_packets

        if self._strict:
            from twisted.python.log import addObserver
            addObserver(unhandled_error_observer)

        self._dispersy.start(autoload_discovery=autoload_discovery)

        if self.master_private_key:
            self._master_member = self._dispersy.get_member(private_key=self.master_private_key)
        else:
            self._master_member = self._dispersy.get_member(public_key=self.master_key)
        self._my_member = self.get_my_member()
        assert self._master_member
        assert self._my_member

        self._do_log()

        self.print_on_change('community-kwargs', {}, self.community_kwargs)
        self.print_on_change('community-env', {}, {'pid':getpid()})

        self._logger.debug("Finished starting dispersy")

    def get_my_member(self):
        return self._dispersy.get_member(private_key=self.my_member_private_key)

    def stop_dispersy(self):
        self._dispersy_exit_status = self._dispersy.stop()

    def stop(self, retry=3):
        retry = int(retry)
        if self._dispersy_exit_status is None and retry:
            reactor.callLater(1, self.stop, retry - 1)
        else:
            self._logger.debug("Dispersy exit status was: %s", self._dispersy_exit_status)
            reactor.callLater(0, reactor.stop)

    def set_master_member(self, pub_key, priv_key=''):
        self.master_key = pub_key.decode("HEX")
        self.master_private_key = priv_key.decode("HEX")

    def online(self, dont_empty=False):
        self._logger.debug("Trying to go online")
        if self._community is None:
            self._logger.debug("online")

            self._logger.debug("join community %s as %s",
                               self._master_member.mid.encode("HEX"),
                               self._my_member.mid.encode("HEX"))
            self._dispersy.on_incoming_packets = self.original_on_incoming_packets
            self._community = self.community_class.init_community(self._dispersy, self._master_member, self._my_member,
                                                                  *self.community_args, **self.community_kwargs)
            self._community.auto_load = False

            assert self.is_online()
            if not dont_empty:
                self.empty_buffer()

            self._logger.debug("Dispersy is using port %s", repr(self._dispersy._endpoint.get_address()))
        else:
            self._logger.debug("online (we are already online)")

    def offline(self):
        self._logger.debug("Trying to go offline")

        if self._community is None and self._is_joined:
            self._logger.debug("offline (we are already offline)")

        else:
            self._logger.debug("offline")
            for community in self._dispersy.get_communities():
                community.unload_community()

            self._community = None
            self._dispersy.on_incoming_packets = lambda *params: None

        if self._database_file == u':memory:':
            self._logger.debug("Be careful with memory databases and nodes going offline, "
                               "you could be losing database because we're closing databases.")

    def is_online(self):
        return self._community != None

    def churn(self, *args):
        self.print_on_change('community-churn', {}, {'args':args})

    def buffer_call(self, func, args, kargs):
        if len(self._online_buffer) == 0 and self.is_online():
            func(*args, **kargs)
        else:
            self._online_buffer.append((func, args, kargs))

    def empty_buffer(self):
        assert self.is_online()

        # perform all tasks which were scheduled while we were offline
        for func, args, kargs in self._online_buffer:
            try:
                func(*args, **kargs)
            except:
                print_exc()

        self._online_buffer = []

    def reset_dispersy_statistics(self):
        self._dispersy._statistics.reset()

    def annotate(self, message):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "annotate", message))
    def peertype(self, peertype):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "peertype", peertype))

    #
    # Aux. functions
    #


    def get_private_keypair_by_id(self, peer_id):
        if str(peer_id) in self.all_vars:
            key = self.all_vars[str(peer_id)]['private_keypair']
            if isinstance(key, basestring):
                key = self.all_vars[str(peer_id)]['private_keypair'] = self._crypto.key_from_private_bin(base64.decodestring(key))
            return key

    def get_private_keypair(self, ip, port):
        port = int(port)
        for peer_dict in self.all_vars.itervalues():
            if peer_dict['host'] == ip and int(peer_dict['port']) == port:
                key = peer_dict['private_keypair']
                if isinstance(key, basestring):
                    key = peer_dict['private_keypair'] = self._crypto.key_from_private_bin(base64.decodestring(key))
                return key

        err("Could not get_private_keypair for", ip, port)

    def str2bool(self, v):
        return v.lower() in ("yes", "true", "t", "1")

    def str2tuple(self, v):
        if len(v) > 1 and v[1] == "t":
            return (int(v[0]), int(v[2:]))
        if len(v) > 1 and v[1] == ".":
            return float(v)
        return int(v)

    def print_on_change(self, name, prev_dict, cur_dict):
        def get_changed_values(prev_dict, cur_dict):
            new_values = {}
            changed_values = {}
            if cur_dict:
                for key, value in cur_dict.iteritems():
                    # convert key to make it printable
                    if not isinstance(key, (basestring, int, long, float)):
                        key = str(key)

                    # if this is a dict, recursively check for changed values
                    if isinstance(value, dict):
                        converted_dict, changed_in_dict = get_changed_values(prev_dict.get(key, {}), value)

                        new_values[key] = converted_dict
                        if changed_in_dict:
                            changed_values[key] = changed_in_dict

                    # else convert and compare single value
                    else:
                        if not isinstance(value, (basestring, int, long, float, Iterable)):
                            value = str(value)

                        new_values[key] = value
                        if prev_dict.get(key, None) != value:
                            changed_values[key] = value

            return new_values, changed_values

        new_values, changed_values = get_changed_values(prev_dict, cur_dict)
        if changed_values:
            self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, name, json.dumps(changed_values)))
            self._stats_file.flush()
            return new_values
        return prev_dict

    @inlineCallbacks
    def _do_log(self):
        try:
            from Tribler.dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME
        except:
            from dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME
        total_stumbled_candidates = defaultdict(lambda:defaultdict(set))

        prev_statistics = {}
        prev_total_received = {}
        prev_total_dropped = {}
        prev_total_delayed = {}
        prev_total_outgoing = {}
        prev_total_fail = {}
        prev_endpoint_recv = {}
        prev_endpoint_send = {}
        prev_created_messages = {}
        prev_bootstrap_candidates = {}

        while True:
            self._dispersy.statistics.update()

            communities_dict = {}
            for c in self._dispersy.statistics.communities:

                if c._community.dispersy_enable_candidate_walker:
                    # determine current size of candidates categories
                    nr_walked = nr_intro = nr_stumbled = 0

                    # we add all candidates which have a last_stumble > now - CANDIDATE_STUMBLE_LIFETIME
                    now = time()
                    for candidate in c._community.candidates.itervalues():
                        if candidate.last_stumble > now - CANDIDATE_STUMBLE_LIFETIME:
                            nr_stumbled += 1

                            mid = candidate.get_member().mid
                            total_stumbled_candidates[c.hex_cid][candidate.last_stumble].add(mid)

                        if candidate.last_walk > now - CANDIDATE_WALK_LIFETIME:
                            nr_walked += 1

                        if candidate.last_intro > now - CANDIDATE_INTRO_LIFETIME:
                            nr_intro += 1
                else:
                    nr_walked = nr_intro = nr_stumbled = "?"

                total_nr_stumbled_candidates = sum(len(members) for members in total_stumbled_candidates[c.hex_cid].values())

                communities_dict[c.hex_cid] = {'classification': c.classification,
                                         'global_time': c.global_time,
                                         'sync_bloom_new': c.sync_bloom_new,
                                         'sync_bloom_reuse': c.sync_bloom_reuse,
                                         'sync_bloom_send': c.sync_bloom_send,
                                         'sync_bloom_skip': c.sync_bloom_skip,
                                         'nr_candidates': len(c.candidates) if c.candidates else 0,
                                         'nr_walked': nr_walked,
                                         'nr_stumbled': nr_stumbled,
                                         'nr_intro' : nr_intro,
                                         'total_stumbled_candidates': total_nr_stumbled_candidates}

            # check for missing communities, reset candidates to 0
            cur_cids = communities_dict.keys()
            for cid, c in prev_statistics.get('communities', {}).iteritems():
                if cid not in cur_cids:
                    _c = c.copy()
                    _c['nr_candidates'] = "?"
                    _c['nr_walked'] = "?"
                    _c['nr_stumbled'] = "?"
                    _c['nr_intro'] = "?"
                    communities_dict[cid] = _c

            statistics_dict = {'conn_type': self._dispersy.statistics.connection_type,
                               'received_count': self._dispersy.statistics.total_received,
                               'success_count': self._dispersy.statistics.msg_statistics.success_count,
                               'drop_count': self._dispersy.statistics.msg_statistics.drop_count,
                               'delay_count': self._dispersy.statistics.msg_statistics.delay_received_count,
                               'delay_success': self._dispersy.statistics.msg_statistics.delay_success_count,
                               'delay_timeout': self._dispersy.statistics.msg_statistics.delay_timeout_count,
                               'delay_send': self._dispersy.statistics.msg_statistics.delay_send_count,
                               'created_count': self._dispersy.statistics.msg_statistics.created_count,
                               'total_up': self._dispersy.statistics.total_up,
                               'total_down': self._dispersy.statistics.total_down,
                               'total_send': self._dispersy.statistics.total_send,
                               'cur_sendqueue': self._dispersy.statistics.cur_sendqueue,
                               'total_candidates_discovered': self._dispersy.statistics.total_candidates_discovered,
                               'walk_attempt': self._dispersy.statistics.walk_attempt_count,
                               'walk_success': self._dispersy.statistics.walk_success_count,
                               'walk_invalid_response_identifier': self._dispersy.statistics.invalid_response_identifier_count,
                               'is_online': self.is_online(),
                               'communities': communities_dict}

            prev_statistics = self.print_on_change("statistics", prev_statistics, statistics_dict)
            prev_total_dropped = self.print_on_change("statistics-dropped-messages", prev_total_dropped, self._dispersy.statistics.msg_statistics.drop_dict)
            prev_total_delayed = self.print_on_change("statistics-delayed-messages", prev_total_delayed, self._dispersy.statistics.msg_statistics.delay_dict)
            prev_total_received = self.print_on_change("statistics-successful-messages", prev_total_received, self._dispersy.statistics.msg_statistics.success_dict)
            prev_total_outgoing = self.print_on_change("statistics-outgoing-messages", prev_total_outgoing, self._dispersy.statistics.msg_statistics.outgoing_dict)
            prev_created_messages = self.print_on_change("statistics-created-messages", prev_created_messages, self._dispersy.statistics.msg_statistics.created_dict)
            prev_total_fail = self.print_on_change("statistics-walk-fail", prev_total_fail, self._dispersy.statistics.walk_failure_dict)
            prev_endpoint_recv = self.print_on_change("statistics-endpoint-recv", prev_endpoint_recv, self._dispersy.statistics.endpoint_recv)
            prev_endpoint_send = self.print_on_change("statistics-endpoint-send", prev_endpoint_send, self._dispersy.statistics.endpoint_send)

            yield deferLater(reactor, 5.0, lambda : None)


def main(client_class):
    from gumby.instrumentation import init_instrumentation
    init_instrumentation()
    setupLogging()
    factory = ExperimentClientFactory({}, client_class)
    logger = logging.getLogger()
    logger.debug("Connecting to: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))
    # Wait for a random amount of time before connecting to try to not overload the server when we have a lot of connections
    reactor.callLater(random() * 10,
                      lambda: reactor.connectTCP(environ['SYNC_HOST'], int(environ['SYNC_PORT']), factory))
    reactor.exitCode = 0
    reactor.run()
    exit(reactor.exitCode)

#
# dispersyclient.py ends here

if __name__ == '__main__':
    import sys
    dc = DispersyExperimentScriptClient({})
    dc._stats_file = sys.stderr

    prev_dict = json.loads('{"created_count": 2, "total_candidates_discovered": 12, "total_down": 107164, "success_count": 1, "total_up": 404, "is_online": true, "communities": {"bd152ce23576a515085268c671351ef37e796856" : {"global_time": 4, "sync_bloom_reuse": 0, "sync_bloom_skip": 0, "nr_stumbled_candidates": 0, "sync_bloom_new": 0, "sync_bloom_send": 0, "classification": "PoliSocialCommunity", "cid": "bd152ce23576a515085268c671351ef37e796856", "nr_candidates": 0}}, "total_send": 1, "received_count": 1}')
    cur_dict = json.loads('{"walk_attempt": 3, "total_down": 108232, "success_count": 6, "total_up": 55585, "communities": {"bd152ce23576a515085268c671351ef37e796856" :{"global_time": 4, "sync_bloom_reuse": 0, "sync_bloom_skip": 0, "nr_stumbled_candidates": 0, "sync_bloom_new": 1, "sync_bloom_send": 1, "classification": "PoliSocialCommunity", "cid": "bd152ce23576a515085268c671351ef37e796856", "nr_candidates": 0}}, "total_send": 30, "received_count": 6}')

    dc.print_on_change('test', prev_dict, cur_dict)
