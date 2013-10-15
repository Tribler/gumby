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

from os import environ, path, chdir, makedirs
from sys import stdout, exit
import logging.config

from gumby.sync import ExperimentClient, ExperimentClientFactory
from gumby.scenario import ScenarioRunner

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.python.log import msg, err, startLogging, PythonLoggingObserver

def call_on_dispersy_thread(func):
    def helper(*args, **kargs):
        args[0]._dispersy.callback.register(func, args, kargs)
    helper.__name__ = func.__name__
    return helper


class DispersyExperimentScriptClient(ExperimentClient):

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

    def startExperiment(self):
        msg("Starting dummy scenario experiment")
        scenario_file_path = path.join(environ['EXPERIMENT_DIR'], "allchannel_1000.scenario")

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


        # TODO(emilon): Move this to the right place
        # TODO(emilon): Do we want to have the .dbs in the output dirs or should they be dumped to /tmp?
        my_dir = path.join(environ['OUTPUT_DIR'], self.my_id)
        makedirs(my_dir)
        chdir(my_dir)

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
                msg("An exception occurred.  Quitting because we are running with --strict enabled.")
                print "Exception was:"

                try:
                    raise exception
                except:
                    from traceback import print_exc
                    print_exc()
                # return fatal=True
                return True
            self._dispersy.callback.attach_exception_handler(exception_handler)

        self._dispersy.start()

        self._master_member = self._dispersy.callback.call(self._dispersy.get_member, (self.master_key,))
        self._my_member = self._dispersy.callback.call(self._dispersy.get_new_member, (u"low",))
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

    #
    # Aux. functions
    #

    def str2bool(self, v):
        return v.lower() in ("yes", "true", "t", "1")

#
# dummy_scenario_experiment_client.py ends here
