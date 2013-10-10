#!/usr/bin/env python
# dummy_scenario_experiment_client.py ---
#
# Filename: dummy_scenario_experiment_client.py
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

from os import environ, path
from random import choice
from string import letters
from sys import stdout, exit, path as pythonpath
from time import time
import json
import logging

from twisted.internet import reactor
from twisted.python.log import startLogging, PythonLoggingObserver, msg

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread
from gumby.sync import ExperimentClientFactory

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


class AllChannelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.allchannel.community import AllChannelCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = AllChannelCommunity
        self.my_channel = None
        self.joined_community = None
        self.torrentindex = 1

        self._stats_file = None

        self.set_community_kwarg('integrate_with_tribler', False)

    def registerCallbacks(self):
        self._stats_file = open("statistics.log", 'w')

        self.scenario_runner.register(self.create, 'create')
        self.scenario_runner.register(self.join, 'join')
        self.scenario_runner.register(self.publish, 'publish')
        self.scenario_runner.register(self.post, 'post')
        self.scenario_runner.register(self.annotate, 'annotate')
        self.scenario_runner.register(self.reset_dispersy_statistics, 'reset_dispersy_statistics')

    def start_dispersy(self):
        from Tribler.community.channel.preview import PreviewChannelCommunity
        from Tribler.community.channel.community import ChannelCommunity

        DispersyExperimentScriptClient.start_dispersy(self)
        self._dispersy.callback.call(self._dispersy.define_auto_load, (ChannelCommunity, (), {"integrate_with_tribler": False}))
        self._dispersy.callback.call(self._dispersy.define_auto_load, (PreviewChannelCommunity, (), {"integrate_with_tribler": False}))

        self.community_args = (self._my_member,)
        self._dispersy.callback.register(self._do_log)

    @call_on_dispersy_thread
    def create(self):
        msg("creating-community")
        from Tribler.community.channel.community import ChannelCommunity
        self.my_channel = ChannelCommunity.create_community(self._dispersy, self._my_member, integrate_with_tribler=False)

        msg("creating-channel-message")
        self.my_channel._disp_create_channel(u'', u'')

    @call_on_dispersy_thread
    def join(self):
        msg("trying-to-join-community")

        cid = self._community._channelcast_db.getChannelIdFromDispersyCID(None)
        if cid:
            community = self._community._get_channel_community(cid)
            if community._channel_id:
                self._community.disp_create_votecast(community.cid, 2, int(time()))

                msg("joining-community")
                self.joined_community = community
                return

        reactor.callLater(1, self.join)

    @call_on_dispersy_thread
    def publish(self, amount=1):
        amount = int(amount)
        torrents = []
        if self.my_channel:
            for _ in xrange(amount):
                infohash = str(self.torrentindex)
                infohash += ''.join(choice(letters) for _ in xrange(20 - len(infohash)))

                name = u''.join(choice(letters) for _ in xrange(100))
                files = []
                for _ in range(10):
                    files.append((u''.join(choice(letters) for _ in xrange(30)), 123455))

                trackers = []
                for _ in range(10):
                    trackers.append(''.join(choice(letters) for _ in xrange(30)))

                files = tuple(files)
                trackers = tuple(trackers)

                self.torrentindex += 1
                torrents.append((infohash, int(time()), name, files, trackers))
        if torrents:
            self.my_channel._disp_create_torrents(torrents)

    @call_on_dispersy_thread
    def post(self, amount=1):
        amount = int(amount)
        if self.joined_community:
            for _ in xrange(amount):
                text = ''.join(choice(letters) for i in xrange(160))
                self.joined_community._disp_create_comment(text, int(time()), None, None, None, None)

    @call_on_dispersy_thread
    def reset_dispersy_statistics(self):
        self._dispersy._statistics.reset()

    def annotate(self, message):
        self._stats_file.write('%f %s %s %s\n' % (time(), self.my_id, "annotate", message))

    def _do_log(self):
        def print_on_change(name, prev_dict, cur_dict):
            new_values = {}
            changed_values = {}
            if cur_dict:
                for key, value in cur_dict.iteritems():
                    if not isinstance(key, (basestring, int, long)):
                        key = str(key)

                    new_values[key] = value
                    if prev_dict.get(key, None) != value:
                        changed_values[key] = value

            if changed_values:
                self._stats_file.write('%f %s %s %s\n' % (time(), self.my_id, name, json.dumps(changed_values)))
                self._stats_file.flush()
                return new_values
            return prev_dict

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

            communities_dict = []
            for c in self._dispersy.statistics.communities:
                communities_dict.append({'cid': c.hex_cid,
                                         'classification': c.classification,
                                         'global_time': c.global_time,
                                         'sync_bloom_new': c.sync_bloom_new,
                                         'sync_bloom_reuse': c.sync_bloom_reuse,
                                         'sync_bloom_send': c.sync_bloom_send,
                                         'sync_bloom_skip': c.sync_bloom_skip,
                                         'nr_candidates': len(c.candidates) if c.candidates else 0})

            statistics_dict = {'conn_type': self._dispersy.statistics.connection_type,
                               'received_count': self._dispersy.statistics.received_count,
                               'success_count': self._dispersy.statistics.success_count,
                               'drop_count': self._dispersy.statistics.drop_count,
                               'delay_count': self._dispersy.statistics.delay_count,
                               'delay_success': self._dispersy.statistics.delay_success,
                               'delay_timeout': self._dispersy.statistics.delay_timeout,
                               'delay_send': self._dispersy.statistics.delay_send,
                               'created_count': self._dispersy.statistics.created_count,
                               'total_up': self._dispersy.statistics.total_up,
                               'total_down': self._dispersy.statistics.total_down,
                               'total_send': self._dispersy.statistics.total_send,
                               'cur_sendqueue': self._dispersy.statistics.cur_sendqueue,
                               'total_candidates_discovered': self._dispersy.statistics.total_candidates_discovered,
                               'walk_attempt': self._dispersy.statistics.walk_attempt,
                               'walk_success': self._dispersy.statistics.walk_success,
                               'walk_bootstrap_attempt': self._dispersy.statistics.walk_bootstrap_attempt,
                               'walk_bootstrap_success': self._dispersy.statistics.walk_bootstrap_success,
                               'walk_reset': self._dispersy.statistics.walk_reset,
                               'walk_invalid_response_identifier': self._dispersy.statistics.walk_invalid_response_identifier,
                               'walk_advice_outgoing_request': self._dispersy.statistics.walk_advice_outgoing_request,
                               'walk_advice_incoming_response': self._dispersy.statistics.walk_advice_incoming_response,
                               'walk_advice_incoming_response_new': self._dispersy.statistics.walk_advice_incoming_response_new,
                               'walk_advice_incoming_request': self._dispersy.statistics.walk_advice_incoming_request,
                               'walk_advice_outgoing_response': self._dispersy.statistics.walk_advice_outgoing_response,
                               'communities': communities_dict}

            prev_statistics = print_on_change("statistics", prev_statistics, statistics_dict)
            prev_total_dropped = print_on_change("statistics-dropped-messages", prev_total_dropped, self._dispersy.statistics.drop)
            prev_total_delayed = print_on_change("statistics-delayed-messages", prev_total_delayed, self._dispersy.statistics.delay)
            prev_total_received = print_on_change("statistics-successful-messages", prev_total_received, self._dispersy.statistics.success)
            prev_total_outgoing = print_on_change("statistics-outgoing-messages", prev_total_outgoing, self._dispersy.statistics.outgoing)
            prev_created_messages = print_on_change("statistics-created-messages", prev_created_messages, self._dispersy.statistics.created)
            prev_total_fail = print_on_change("statistics-walk-fail", prev_total_fail, self._dispersy.statistics.walk_fail)
            prev_endpoint_recv = print_on_change("statistics-endpoint-recv", prev_endpoint_recv, self._dispersy.statistics.endpoint_recv)
            prev_endpoint_send = print_on_change("statistics-endpoint-send", prev_endpoint_send, self._dispersy.statistics.endpoint_send)
            prev_bootstrap_candidates = print_on_change("statistics-bootstrap-candidates", prev_bootstrap_candidates, self._dispersy.statistics.bootstrap_candidates)

            yield 1.0


def main():
    config_file = path.join(environ['EXPERIMENT_DIR'], "logger.conf")
    # TODO(emilon): Document this on the user manual
    if path.exists(config_file):
        msg("This experiment has a logger.conf, using it.")
        logging.config.fileConfig(config_file)
    else:
        msg("No logger.conf found for this experiment.")

    factory = ExperimentClientFactory({"random_key": "random value"}, AllChannelClient)
    reactor.connectTCP(environ['HEAD_NODE'], int(environ['SYNC_PORT']), factory)

    reactor.exitCode = 0
    reactor.run()
    exit(reactor.exitCode)

if __name__ == '__main__':
    # TODO(emilon): Temporary hack to work around the missing EXPERIMENT_DIR env var, export it in run_in_env
    environ['EXPERIMENT_DIR'] = path.abspath(path.dirname(__file__))
    startLogging(stdout)
    observer = PythonLoggingObserver()
    observer.start()
    main()

#
# dummy_scenario_experiment_client.py ends here
