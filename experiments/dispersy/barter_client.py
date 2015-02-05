#!/usr/bin/env python
# bartercast_client.py ---
#
# Filename: bartercast_client.py
# Description:
# Author: Cor-Paul Bezemer
# Maintainer:
# Created: Wed Oct 15 16:43:53 2014 (+0200)

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
from sys import path as pythonpath

from gumby.experiments.dispersyclient import main
from allchannel_client import AllChannelClient

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

from Tribler.dispersy.candidate import Candidate
from Tribler.dispersy.statistics import BartercastStatisticTypes


class BarterClient(AllChannelClient):
    def __init__(self, *argv, **kwargs):
        AllChannelClient.__init__(self, *argv, **kwargs)

    def start_dispersy(self, crawl=False):
        from Tribler.community.bartercast4.community import BarterCommunity
        AllChannelClient.start_dispersy(self)
        if crawl:
            from Tribler.community.bartercast4.community import BarterCommunityCrawler
            # communities = self._dispersy.define_auto_load(BarterCommunityCrawler, self._my_member, (), {"integrate_with_tribler": False}, load=True)
            communities = self._dispersy.define_auto_load(BarterCommunityCrawler, self._my_member, (), load=True)
        else:
            # communities = self._dispersy.define_auto_load(BarterCommunity, self._my_member, (), {"integrate_with_tribler": False}, load=True)
            communities = self._dispersy.define_auto_load(BarterCommunity, self._my_member, (), load=True)

        for c in communities:
            if isinstance(c, BarterCommunity):
                self._bccommunity = c

    def registerCallbacks(self):
        AllChannelClient.registerCallbacks(self)
        self.scenario_runner.register(self.request_stats, 'request-stats')

    def request_stats(self, candidate_id=0):
        if not self._bccommunity:
            print "problem: barter community not loaded"
        # candidate = Candidate((str(self.all_vars[candidate_id]['host']), self.all_vars[candidate_id]['port']), False)
        # self._bccommunity.create_stats_request(candidate, BartercastStatisticTypes.TORRENTS_RECEIVED)
        for c in self.all_vars.itervalues():
            candidate = Candidate((str(c['host']), c['port']), False)
            self._bccommunity.create_stats_request(candidate, BartercastStatisticTypes.TORRENTS_RECEIVED)


if __name__ == '__main__':
    BarterClient.scenario_file = "barter10.scenario"
    main(BarterClient)

#
# demers_client.py ends here