#!/usr/bin/env python
# extract_social_statistics.py ---
#
# Filename: extract_social_statistics.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:

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


from itertools import groupby
from extract_dispersy_statistics import *

class EncMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)
        self.churn = -1

        self.received_foaf = 0
        self.received_friend = 0

        self.encrypted_foaf = 0
        self.encrypted_friend = 0

        self.send_received = defaultdict(lambda : {'received_encrypted':[]})

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key in ["text-statistics", "encrypted-statistics", "community-churn"]

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        if key == 'community-churn':
            self.churn = json['args'][1]
        else:
            identifier = json['created_by'] + '@' + str(json['global_time'])
            if key == "text-statistics":
                if json['from_friend']:
                    self.received_friend += 1
                if json['from_foaf']:
                    self.received_foaf += 1

                self.send_received[identifier]['received'] = timestamp

            elif key == 'encrypted-statistics':
                if json['created_by_me']:
                    self.send_received[identifier]['created'] = timestamp
                else:
                    self.send_received[identifier]['received_encrypted'].append(timestamp)
                    if json['from_friend']:
                        self.encrypted_friend += 1
                    if json['from_foaf']:
                        self.encrypted_foaf += 1

    def all_files_done(self, extract_statistics):
        f = open(os.path.join(extract_statistics.node_directory, "_received_from.txt"), 'w')
        print >> f, "churn type Friend Foaf"
        print >> f, self.churn, "text", self.received_friend, self.received_foaf
        print >> f, self.churn, "encrypted", self.encrypted_friend, self.encrypted_foaf
        f.close()

        if self.send_received:
            f = open(os.path.join(extract_statistics.node_directory, "_received_after.txt"), 'w')
            print >> f, "churn identifier created received replicas"
            for identifier, received_dict in self.send_received.iteritems():
                if 'created' in received_dict and 'received' in received_dict:
                    print >> f, self.churn, identifier, received_dict['created'], received_dict['received'], len(received_dict['received_encrypted'])
            f.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <node-directory> <messagestoplot>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        sys.exit(1)

    e = get_parser(sys.argv)
    e.add_handler(EncMessages())
    e.parse()

#
# extract_social_statistics.py ends here
