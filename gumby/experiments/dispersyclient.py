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

from os import environ, path, chdir, makedirs, symlink
from sys import stdout, exit
import logging.config
import logging
import json
from time import time

from gumby.sync import ExperimentClient, ExperimentClientFactory
from gumby.scenario import ScenarioRunner
from gumby.log import PythonLoggingObserver

# TODO(emilon): Make sure that the automatically chosen one is not this one in case we can avoid this.
# The reactor needs to be imported after the dispersy client, as it is installing an EPOLL based one.
from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.python.log import msg, startLogging


def call_on_dispersy_thread(func):
    def helper(*args, **kargs):
        args[0]._dispersy.callback.register(func, args, kargs)
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

    def startExperiment(self):
        msg("Starting dummy scenario experiment")
        scenario_file_path = path.join(environ['EXPERIMENT_DIR'], self.scenario_file)

        self.scenario_runner = ScenarioRunner(scenario_file_path, int(self.my_id))
        # TODO(emilon): Auto-register this stuff
        self.scenario_runner.register(self.echo)
        self.scenario_runner.register(self.online)
        self.scenario_runner.register(self.offline)
        self.scenario_runner.register(self.set_community_kwarg)
        self.scenario_runner.register(self.set_database_file)
        self.scenario_runner.register(self.use_memory_database)
        self.scenario_runner.register(self.set_ignore_exceptions)
        self.scenario_runner.register(self.start_dispersy)
        self.scenario_runner.register(self.stop_dispersy)
        self.scenario_runner.register(self.stop)
        self.scenario_runner.register(self.set_master_member)
        self.scenario_runner.register(self.reset_dispersy_statistics, 'reset_dispersy_statistics')
        self.scenario_runner.register(self.annotate, 'annotate')

        # TODO(emilon): Move this to the right place
        # TODO(emilon): Do we want to have the .dbs in the output dirs or should they be dumped to /tmp?
        my_dir = path.join(environ['OUTPUT_DIR'], self.my_id)
        makedirs(my_dir)
        chdir(my_dir)
        self._stats_file = open("statistics.log", 'w')

        # TODO(emilon): Fix me or kill me
        try:
            symlink(path.join(environ['PROJECT_DIR'], 'tribler', 'bootstraptribler.txt'), 'bootstraptribler.txt')
        except OSError:
            pass

        self.registerCallbacks()

        self.scenario_runner.run()

    def registerCallbacks(self):
        pass

    #
    # Actions
    #

    def echo(self, *argv):
        msg("%s ECHO" % self.my_id, ' '.join(argv))

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

    def start_dispersy(self):
        msg("Starting dispersy")
        # We need to import the stuff _AFTER_ configuring the logging stuff.
        from Tribler.dispersy.callback import Callback
        from Tribler.dispersy.dispersy import Dispersy
        from Tribler.dispersy.endpoint import StandaloneEndpoint

        self._dispersy = Dispersy(Callback("Dispersy"), StandaloneEndpoint(int(self.my_id) + 12000, '0.0.0.0'), u'.', self._database_file)
        self._dispersy.statistics.enable_debug_statistics(True)

        if self._strict:
            def exception_handler(exception, fatal):
                msg("An exception occurred. Quitting because we are running with strict enabled.")
                print "Exception was:"

                try:
                    raise exception
                except:
                    from traceback import print_exc
                    print_exc()
                # Set Dispersy's exit status to error
                self._dispersy_exit_status = 1
                # Stop the experiment
                reactor.callLater(1, self.stop)

                # return fatal=True
                return True
            self._dispersy.callback.attach_exception_handler(exception_handler)

        self._dispersy.start()

        self._master_member = self._dispersy.callback.call(self._dispersy.get_member, (self.master_key,))
        self._my_member = self._dispersy.callback.call(self._dispersy.get_new_member, (u"low",))

        self._dispersy.callback.register(self._do_log)
        msg("Finished starting dispersy")

    def stop_dispersy(self):
        def onDispersyStopped(result):
            self._dispersy_exit_status = result

        d = deferToThread(self._dispersy.stop)
        d.addCallback(onDispersyStopped)

    def stop(self, retry=3):
        retry = int(retry)
        if self._dispersy_exit_status is None and retry:
                reactor.callLater(1, self.stop, retry - 1)
        else:
                msg("Dispersy exit status was:", self._dispersy_exit_status)
                reactor.callLater(0, reactor.stop)

    def set_master_member(self, pub_key):
        self.master_key = pub_key.decode("HEX")

    @call_on_dispersy_thread
    def online(self):
        msg("Trying to go online")
        if self._community is None:
            msg("online")

            if self._is_joined:
                self._community = self.community_class.load_community(self._dispersy, self._master_member, *self.community_args, **self.community_kwargs)

            else:
                msg("join community %s as %s", self._master_member.mid.encode("HEX"), self._my_member.mid.encode("HEX"))
                self._community = self.community_class.join_community(self._dispersy, self._master_member, self._my_member, *self.community_args, **self.community_kwargs)
                self._community.auto_load = False
                self._is_joined = True
        else:
            msg("online (we are already online)")

    @call_on_dispersy_thread
    def offline(self):
        if self._community is None:
            msg("offline (we are already offline)")
        else:
            msg("offline")
            for community in self._dispersy.get_communities():
                community.unload_community()
            self._community = None

    @call_on_dispersy_thread
    def reset_dispersy_statistics(self):
        self._dispersy._statistics.reset()

    def annotate(self, message):
        self._stats_file.write('%f %s %s %s\n' % (time(), self.my_id, "annotate", message))

    #
    # Aux. functions
    #
    def str2bool(self, v):
        return v.lower() in ("yes", "true", "t", "1")

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


def main(client_class):
    startLogging(stdout)
    observer = PythonLoggingObserver()
    observer.start()
    config_file = path.join(environ['EXPERIMENT_DIR'], "logger.conf")
    # TODO(emilon): Document this on the user manual
    if path.exists(config_file):
        msg("This experiment has a logger.conf, using it.")
        logging.config.fileConfig(config_file)
    else:
        msg("No logger.conf found for this experiment.")

    factory = ExperimentClientFactory({}, client_class)
    reactor.connectTCP(environ['HEAD_NODE'], int(environ['SYNC_PORT']), factory)

    reactor.exitCode = 0
    reactor.run()
    exit(reactor.exitCode)

#
# dummy_scenario_experiment_client.py ends here
