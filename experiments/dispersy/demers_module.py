#!/usr/bin/env python2
# demers_module.py ---
#
# Filename: demers_module.py
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

from random import choice
from string import letters

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_launcher import CommunityLauncher
from gumby.modules.community_experiment_module import CommunityExperimentModule

from Tribler.community.demers.community import DemersTest


@static_module
class DemersCommunityLauncher(CommunityLauncher):
    def get_community_class(self):
        return DemersTest


class DemersModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(DemersModule, self).__init__(experiment, DemersTest)
        # this community is not loaded by default, so add a launcher for it
        self.set_community_launcher(DemersCommunityLauncher())

    @experiment_callback
    def publish(self, amount=1):
        amount = int(amount)
        for _ in xrange(amount):
            self._logger.debug('creating-text')
            text = u''.join(choice(letters) for _ in xrange(100))
            self.community.create_text(text)
