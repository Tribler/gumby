#!/usr/bin/env python
# extract_privatesearch_statistics.py ---
#
# Filename: extract_privatesearch_statistics.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Mon Dec 2 18:10:17 2013 (+0200)

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

class SearchMessages(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

        self.searches = defaultdict(list)
        self.search_responses = {}
        self.ttl = "?"

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key in ["search-statistics", "search-response", 'community-kwargs']

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        if key == "search-statistics":
            identifier = json['identifier']
            created_by_me = json.get('created_by_me', False)
            cycle = json.get('cycle', False)

            self.searches[identifier].append((timeoffset, created_by_me, cycle, node_nr))
        elif key == 'search-response':
            identifier = json['identifier']
            self.search_responses[identifier] = min(self.search_responses.get(identifier, timeoffset), timeoffset)
        elif 'ttl' in json:
            self.ttl = self.tuple2str(json['ttl'])

    def all_files_done(self, extract_statistics):
        if self.searches:
            f = open(os.path.join(extract_statistics.node_directory, "searches.txt"), 'w')
            print >> f, "ttl identifier duration nrmessages nrcycles nruniquenodes took"
            for identifier, nodes in self.searches.iteritems():
                nr_collisions = sum(created for _, created, _, _ in nodes)
                if nr_collisions > 1:
                    print >> sys.stderr, "skipping", identifier, "got", nr_collisions, "nodes creating it"
                    continue

                duration = max(timeoffset for timeoffset, _, _, _ in nodes) - min(timeoffset for timeoffset, _, _, _ in nodes)
                nr_cycles = sum(cycle for _, _, cycle, _ in nodes)
                nr_messages = len(nodes) - 1  # substracting search creator
                nr_unique_nodes = len(set(nodename for _, _, _, nodename in nodes)) - 1

                if identifier in self.search_responses:
                    took = self.search_responses[identifier] - min(timeoffset for timeoffset, _, _, _ in nodes)
                else:
                    took = -1

                print >> f, self.ttl, identifier, duration, nr_messages, nr_cycles, nr_unique_nodes, took

            f.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <node-directory> <messagestoplot>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        sys.exit(1)

    e = get_parser(sys.argv)
    e.add_handler(SearchMessages())
    e.parse()

#
# extract_privatesearch_statistics.py ends here
