import fnmatch
import os
import re


class StatisticsParser(object):
    """
    This class is responsible for parsing statistics after an experiment ends.
    """

    def __init__(self, node_directory):
        self.node_directory = node_directory

    def yield_files(self, file_pattern):
        peer_pattern = re.compile('[0-9]+')

        def find_matching_files(directory):
            """
            Recursively find files matching a specific pattern.
            Returns the list of (absolute) filenames of files that match the pattern.
            """
            matching_files = []
            for root, _, files in os.walk(directory):
                for basename in files:
                    if fnmatch.fnmatch(basename, file_pattern):
                        filename = os.path.join(root, basename)
                        matching_files.append(filename)
            return matching_files

        # DAS structure
        for headnode in os.listdir(self.node_directory):
            headdir = os.path.join(self.node_directory, headnode)
            if os.path.isdir(headdir):
                for node in os.listdir(headdir):
                    nodedir = os.path.join(self.node_directory, headnode, node)
                    if os.path.isdir(nodedir):
                        for peer in os.listdir(nodedir):
                            peerdir = os.path.join(self.node_directory, headnode, node, peer)
                            if os.path.isdir(peerdir) and peer_pattern.match(peer):
                                try:
                                    peer_nr = int(peer)

                                    dir_path = os.path.join(self.node_directory, headnode, node, peer)
                                    matching_files = find_matching_files(dir_path)
                                    for matching_file in matching_files:
                                        if os.stat(matching_file).st_size > 0:
                                            yield peer_nr, matching_file, peerdir
                                except ValueError:
                                    break

        # Localhost structure
        for peer in os.listdir(self.node_directory):
            peerdir = os.path.join(self.node_directory, peer)
            if os.path.isdir(peerdir) and peer_pattern.match(peer):
                peer_nr = int(peer)

                dir_path = os.path.join(self.node_directory, peer)
                matching_files = find_matching_files(dir_path)
                for matching_file in matching_files:
                    if os.stat(matching_file).st_size > 0:
                        yield peer_nr, matching_file, peerdir

    def run(self):
        pass
