#!/usr/bin/env python
# extract_demers_statistics.py ---
#
# Filename: extract_demers_statistics.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Oct 23 18:41:17 2013 (+0200)

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


class DemersMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        # at what timeoffset a peer received this piece
        self.pieces_received = defaultdict(defaultdict)

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key == "statistics-successful-messages" or key == "statistics-created-messages"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        for key, value in json.iteritems():
            if key == "text" and node_nr not in self.pieces_received[value]:
                self.pieces_received[value][node_nr] = timeoffset

    def all_files_done(self, extract_statistics):
        # modify self.pieces_received into flat piece, timeoffset dict
        pieces_received = defaultdict(list)
        for piece, peers in self.pieces_received.iteritems():
            for peer in peers:
                pieces_received[piece].append(self.pieces_received[piece][peer])

        h_received_records = open(os.path.join(extract_statistics.node_directory, "received_text_records.txt"), "w+")
        print >> h_received_records, "#nrpeers, took, partnr"

        for piece, piece_received in pieces_received.iteritems():
            piece_received.sort()

            peers_received = 0
            for timeoffset, peers in groupby(piece_received):
                peers_received += len(list(peers))
                print >> h_received_records, peers_received, timeoffset - piece_received[0], piece

        h_received_records.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <node-directory> <messagestoplot>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        sys.exit(1)

    e = get_parser(sys.argv)
    e.add_handler(DemersMessages())
    e.parse()

#
# extract_demers_statistics.py ends here
