#!/usr/bin/env python2
import json
import os
import re
import sys

from itertools import chain
from collections import defaultdict

from twisted.python import log


class DHTStatisticsParser(object):
    """
    This class is responsible for parsing statistics of the DHT
    """

    def __init__(self, node_directory):
        self.node_directory = node_directory

    def yield_files(self, file_to_check='dht.log'):
        pattern = re.compile('[0-9]+')

        # DAS structure
        for headnode in os.listdir(self.node_directory):
            headdir = os.path.join(self.node_directory, headnode)
            if os.path.isdir(headdir):
                for node in os.listdir(headdir):
                    nodedir = os.path.join(self.node_directory, headnode, node)
                    if os.path.isdir(nodedir):
                        for peer in os.listdir(nodedir):
                            peerdir = os.path.join(self.node_directory, headnode, node, peer)
                            if os.path.isdir(peerdir) and pattern.match(peer):
                                peer_nr = int(peer)

                                filename = os.path.join(self.node_directory, headnode, node, peer, file_to_check)
                                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                                    yield peer_nr, filename, peerdir

        # Localhost structure
        for peer in os.listdir(self.node_directory):
            peerdir = os.path.join(self.node_directory, peer)
            if os.path.isdir(peerdir) and pattern.match(peer):
                peer_nr = int(peer)

                filename = os.path.join(self.node_directory, peer, file_to_check)
                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                    yield peer_nr, filename, peerdir

    def aggregate_dht_response_times(self):
        with open('dht_response_times.csv', 'w', 0) as csv_fp:
            csv_fp.write('peer time operation response_time\n')
            for peer_nr, filename, dir in self.yield_files():
                with open(filename) as log_fp:
                    for line in log_fp.readlines():
                        ts, method, t = line.split()
                        csv_fp.write('%s %s %s %s\n' % (peer_nr, ts, method, t))

    def run(self):
        self.aggregate_dht_response_times()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

observer = log.PythonLoggingObserver()
observer.start()

parser = DHTStatisticsParser(sys.argv[1])
parser.run()
