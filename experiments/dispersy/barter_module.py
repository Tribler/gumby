#!/usr/bin/env python2
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


from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_launcher import BarterCommunityLauncher
from gumby.modules.community_experiment_module import CommunityExperimentModule

from Tribler.dispersy.candidate import Candidate
from Tribler.community.bartercast4.community import BarterCommunity, BarterCommunityCrawler
from Tribler.community.bartercast4.statistics import BartercastStatisticTypes


class BarterCrawlerCommunityLauncher(BarterCommunityLauncher):
    def get_community_class(self):
        return BarterCommunityCrawler


@static_module
class BarterModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(BarterModule, self).__init__(experiment, BarterCommunity)

    @experiment_callback
    def enable_crawler(self):
        self.community_loader.del_launcher(self.community_launcher)
        self.set_community_launcher(BarterCrawlerCommunityLauncher())

    @experiment_callback
    def request_stats(self, candidate_id=0):
        """
        Requests statistics from every candidate or a specific candidate
        :param candidate_id: The candidate id from the node that the stats will be requested from.
        """
        if not self.community:
            self._logger.error("barter community not loaded")
        if candidate_id == 0:
            # Send a message to all candidate.
            for c in self.all_vars.itervalues():
                candidate = Candidate((str(c['host']), c['port']), False)
                self.community.create_stats_request(candidate, BartercastStatisticTypes.TORRENTS_RECEIVED)
        else:
            # Send a message to a specific candidate.
            target = self.all_vars[candidate_id]
            candidate = Candidate((str(target['host']), target['port']), False)
            self.community.create_stats_request(candidate, BartercastStatisticTypes.TORRENTS_RECEIVED)
