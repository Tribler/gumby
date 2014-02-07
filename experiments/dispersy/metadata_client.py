#!/usr/bin/env python
# social_client.py ---
#
# Filename: social_client.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Mon Oct 28 14:10:00 2013 (+0200)

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
import sys
from os import path, environ
from time import time
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main, \
    buffer_online

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class MetadataClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.metadata.community import MetadataCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = MetadataCommunity

        self.set_community_kwarg('integrate_with_tribler', False)

    def registerCallbacks(self):
        self.scenario_runner.register(self.insert_metadata, 'insert_metadata')

    @call_on_dispersy_thread
    def insert_metadata(self, hash_data="", amount=1):
        amount = int(amount)
        for _ in xrange(amount):
            msg('creating-metadata')

            from Tribler.community.metadata.payload import METADATA_HASHTYPE_BITTORRENT, METADATA_HASHTYPE_SWIFT
            hash_type = METADATA_HASHTYPE_BITTORRENT
            hash_value = sha1(hash_data).digest()
            data_list = [(u"name", u"test-metadata"), (u"category", u"test")]

            self._community.create_metadata_message(hash_type, hash_value, data_list)


if __name__ == '__main__':
    MetadataClient.scenario_file = environ.get('SCENARIO_FILE', 'metadata.scenario')
    main(MetadataClient)

#
# metadata_client.py ends here
