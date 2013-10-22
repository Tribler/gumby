#!/usr/bin/env python
# demers_client.py ---
#
# Filename: demers_client.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Mon Oct 21 16:43:53 2013 (+0200)

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

from os import path
from random import choice
from string import letters
from sys import path as pythonpath
from time import time

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main

from twisted.python.log import msg

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

    def start_dispersy(self):
        from Tribler.community.demers.community import DemersTest

        DispersyExperimentScriptClient.start_dispersy(self)
        self._dispersy.callback.call(self._dispersy.define_auto_load, (DemersTest, (), {"integrate_with_tribler": False}))

        self.community_args = (self._my_member,)

    @call_on_dispersy_thread
    def create(self):
        msg("creating-community")
        from Tribler.community.demers.community import DemersTest
        self.my_channel = DemersTest.create_community(self._dispersy, self._my_member, integrate_with_tribler=False)

    @call_on_dispersy_thread
    def join(self):
        from Tribler.community.demers.community import DemersTest
        msg("trying-to-join-community")

        master = self._dispersy.get_member(self.master_key)
        if master:
            community =  DemersTest.join_community(self._dispersy, master, self.my_member)
            if community:
                self._community = community
            else:
                self._dispersy.callback.register(self.join, delay=1.0)

    @call_on_dispersy_thread
    def publish(self, amount=1):
        amount = int(amount)
        torrents = []
        if self.my_channel:
            for _ in xrange(amount):
                msg('creating-text')
                text = u''.join(choice(letters) for _ in xrange(100))
                self._community.create_text(text)

        if torrents:
            self.my_channel._disp_create_torrents(torrents)

    @call_on_dispersy_thread
    def post(self, amount=1):
        amount = int(amount)
        if self.joined_community:
            for _ in xrange(amount):
                text = ''.join(choice(letters) for i in xrange(160))
                self.joined_community._disp_create_comment(text, int(time()), None, None, None, None)


if __name__ == '__main__':
    main(AllChannelClient)

#
# demers_client.py ends here
