#!/usr/bin/env python2
# dummy_scenario_experiment_client.py ---
#
# Filename: allchannel_client.py
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
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from twisted.internet.task import LoopingCall

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main


# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.community.channel.community import ChannelCommunity


class AllChannelClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.allchannel.community import AllChannelCommunity
        super(AllChannelClient, self).__init__(*argv, **kwargs)
        self.community_class = AllChannelCommunity
        self.my_channel = None
        self.joined_community = None
        self.torrentindex = 1

        self.dc_lc = LoopingCall(self.print_delayed_calls)
        self.dc_lc.start(5.0, now=False)

        reactor.callLater(10, self.publish)

        self.join_lc = None
        self.set_community_kwarg('tribler_session', None)

    def registerCallbacks(self):
        self.scenario_runner.register(self.create, 'create')
        self.scenario_runner.register(self.join, 'join')
        self.scenario_runner.register(self.publish, 'publish')
        self.scenario_runner.register(self.post, 'post')

    @inlineCallbacks
    def start_dispersy(self):
        from Tribler.community.channel.preview import PreviewChannelCommunity

        yield super(AllChannelClient, self).start_dispersy()
        yield self._dispersy.define_auto_load(ChannelCommunity, self._my_member, (), {"tribler_session": None})
        yield self._dispersy.define_auto_load(PreviewChannelCommunity, self._my_member, (), {"tribler_session": None})

    @inlineCallbacks
    def create(self):
        self._logger.info("creating-community")
        self.my_channel = yield ChannelCommunity.create_community(self._dispersy, self._my_member, tribler_session=None)
        yield self.my_channel.set_channel_mode(ChannelCommunity.CHANNEL_OPEN)

        self._logger.info("Community created with member: %s", self.my_channel._master_member)
        yield self.my_channel._disp_create_channel(u'', u'')


    def print_delayed_calls(self):
        delayed_calls = reactor.getDelayedCalls()
        if delayed_calls:
            for dc in delayed_calls:
                self._logger.error("DELAYED CALL: %s", dc)

    @inlineCallbacks
    def join(self):
        if not self.join_lc:
            self.join_lc = lc = LoopingCall(self.join)
            lc.start(1.0, now=False)

        self._logger.info("trying-to-join-community")

        cid = self._community._channelcast_db.getChannelIdFromDispersyCID(None)
        self._logger.error("CID %s IN COMMUNITY %s FROM %s", cid, self._community,
                           self._community._channelcast_db.getChannelIdFromDispersyCID)
        if cid:
            community = yield self._community._get_channel_community(cid)
            self._logger.error("community._channel_id %s", community._channel_id)
            if community._channel_id:
                yield self._community.disp_create_votecast(community.cid, 2, int(time()))

                self._logger.info("joining-community")
                for c in self._dispersy.get_communities():
                    if isinstance(c, ChannelCommunity):
                        self.joined_community = c
                if self.joined_community is None:
                    self._logger.info("couldn't join community")
                self._logger.info("Joined community with member: %s", self.joined_community._master_member)
                self.join_lc.stop()
                return

    def publish(self, amount=1):
        amount = int(amount)
        k_for_crash = 1/0
        self._logger.error("in publish, 1")
        torrents = []
        if self.my_channel or self.joined_community:
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
                self._logger.error("in publish, 2")
                torrents.append((infohash, int(time()), name, files, trackers))
        if torrents:
            if self.my_channel:
                yield self.my_channel._disp_create_torrents(torrents)
            elif self.joined_community:
                yield self.joined_community._disp_create_torrents(torrents)

    def post(self, amount=1):
        amount = int(amount)
        if self.joined_community:
            for _ in xrange(amount):
                text = ''.join(choice(letters) for i in xrange(160))
                yield self.joined_community._disp_create_comment(text, int(time()), None, None, None, None)

if __name__ == '__main__':
    AllChannelClient.scenario_file = 'allchannel_1000.scenario'
    main(AllChannelClient)

#
# allchannel_client.py ends here
