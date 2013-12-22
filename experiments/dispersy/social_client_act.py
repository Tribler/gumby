#!/usr/bin/env python
# social_client_act.py ---
#
# Filename: social_client.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Fri Dec 20 12:49:00 2013 (+0200)

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

from experiments.dispersy.social_client import SocialClient
from gumby.experiments.dispersyclient import main

if __name__ == '__main__':
    SocialClient.scenario_file = "social_act_processed.scenario"
    main(SocialClient)

#
# social_client_act.py ends here
