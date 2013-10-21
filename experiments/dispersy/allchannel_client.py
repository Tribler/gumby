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
        self.scenario_runner.register(self.annotate, 'annotate')

    def start_dispersy(self):
        from Tribler.community.channel.preview import PreviewChannelCommunity
        from Tribler.community.channel.community import ChannelCommunity

        DispersyExperimentScriptClient.start_dispersy(self)
        self._dispersy.callback.call(self._dispersy.define_auto_load, (ChannelCommunity, (), {"integrate_with_tribler": False}))
        self._dispersy.callback.call(self._dispersy.define_auto_load, (PreviewChannelCommunity, (), {"integrate_with_tribler": False}))

        self.community_args = (self._my_member,)

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

        self._dispersy.callback.register(self.join, delay=1.0)

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


if __name__ == '__main__':
    main(AllChannelClient)

#
# dummy_scenario_experiment_client.py ends here
