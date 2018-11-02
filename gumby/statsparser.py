import os
import re


class StatisticsParser(object):
    """
    This class is responsible for parsing statistics after an experiment ends.
    """

    def __init__(self, node_directory):
        self.node_directory = node_directory

    def yield_files(self, file_to_check):
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
                                try:
                                    peer_nr = int(peer)

                                    filename = os.path.join(self.node_directory, headnode, node, peer, file_to_check)
                                    if os.path.exists(filename) and os.stat(filename).st_size > 0:
                                        yield peer_nr, filename, peerdir
                                except ValueError:
                                    break

        # Localhost structure
        for peer in os.listdir(self.node_directory):
            peerdir = os.path.join(self.node_directory, peer)
            if os.path.isdir(peerdir) and pattern.match(peer):
                peer_nr = int(peer)

                filename = os.path.join(self.node_directory, peer, file_to_check)
                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                    yield peer_nr, filename, peerdir

    def run(self):
        pass
