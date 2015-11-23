import os
from os import path
import base64

import networkx as nx

from Tribler.community.multichain.database import MultiChainDB
from Tribler.community.multichain.payload import EMPTY_HASH
from Tribler.community.multichain.community import GENESIS_ID
from Tribler.community.multichain.conversion import PK_LENGTH

EMPTY_HASH_ENCODED = base64.encodestring(EMPTY_HASH)
GENESIS_ID_ENCODED = base64.encodestring(GENESIS_ID)


class MultiChainExperimentAnalysisDatabase(MultiChainDB):
    """
    Extended MultiChain experiments that provides additional analysis functionality to analysis a experiment.
    """

    def __init__(self, dispersy, working_directory):
        super(MultiChainExperimentAnalysisDatabase, self).__init__(dispersy, working_directory)

    def get_totals(self, mid):
        """
        Return the totals in order by sequence number for mid.
        """
        mid = buffer(mid)
        db_query = u"SELECT total_up, total_down FROM(" \
                   u"SELECT total_up_responder as total_up, total_down_responder as total_down, sequence_number_responder " \
                   u"as sequence_number FROM multi_chain WHERE mid_responder == ? AND sequence_number_responder != -1 "\
                   u"UNION " \
                   u"SELECT total_up_requester as total_up, total_down_requester " \
                   u"as total_down, sequence_number_requester as sequence_number FROM multi_chain WHERE mid_requester =?) " \
                   u"ORDER BY sequence_number"
        db_result = self.execute(db_query, (mid, mid)).fetchall()
        return db_result


class DatabaseReader(object):

    def __init__(self, working_directory):
        """
        Parent class that contains functionality for both gumby and single database readers.
        DatabaseReaders process experimentation information.
        """
        """ Either contains all information all ready or all information will be aggregated here."""
        self.working_directory = working_directory
        self.database = self.get_database(self.working_directory)
        self.graph = nx.DiGraph()
        """ Mids are retrieved during generate_graph and used in generate_totals"""
        self.mids = set([])

        self.generate_graph()
        self.generate_totals()
        return

    def get_database(self, db_path):
        raise NotImplementedError("Abstract method")

    def generate_graph(self):
        """
        Generates a gexf file of the graph.
        """
        raise NotImplementedError("Abstract method")

    def add_block_to_graph(self, block_id, block):
        # The block.id is not usable because it differs from the actual hash as the PKs are missing.
        block_id_encoded = base64.encodestring(block_id)
        # Add the block to the graph
        self.graph.add_node(block_id_encoded)
        # Add the edges of the blocks
        self.graph.add_edge(block_id_encoded, base64.encodestring(block.previous_hash_requester))
        self.graph.add_edge(block_id_encoded, base64.encodestring(block.previous_hash_responder))
        if block.previous_hash_requester == block.previous_hash_responder:
            """ Follow up block"""
            # Color = blue
            self.paint_node(block_id_encoded, 'b')

        # Add mid's to list
        self.mids.add(block.mid_requester)
        self.mids.add(block.mid_responder)

    def _work_empty_hash(self):
        """
        Fix the graph related to the empty hash nodes.
        """
        print "Fixing the EMPTY HASH nodes."
        # Color = Red
        self._work_color(EMPTY_HASH_ENCODED, 'r')

    def _work_genesis_hash(self):
        """
        Fix the graph related tot the genesis hash nodes.
        """
        print "Fixing the GENESIS HASH nodes."
        # Color = Green
        self._work_color(GENESIS_ID_ENCODED, 'g')

    def _work_color(self, node_id, color):
        """
        Fix the graph by removing the node with node_id and adding the color to nodes with incoming edges to node_id.
        """
        edges = self.graph.in_edges(node_id)
        nodes = [edge[0] for edge in edges]
        for node in nodes:
            self.paint_node(node, color)
        if self.graph.__contains__(node_id):
            self.graph.remove_node(node_id)

    def paint_node(self, node, color):
        color_data = {'r': 0, 'g': 0, 'b': 0, 'a': 0}
        if color == 'r':
            color_data['r'] = 255
        elif color == 'b':
            color_data['b'] = 255
        elif color == 'g':
            color_data['g'] = 255
        self.graph.node[node]['viz'] = {'color': color_data}

    def _write_graph(self):
        nx.write_gexf(self.graph, os.path.join(self.working_directory, "graph-gumby.gexf"), encoding='utf8',
                      prettyprint=False, version="1.2draft")

    def generate_totals(self):
        """
        Generates a file containing all totals in a R format.
        """
        print("Reading totals")
        mid_data = dict.fromkeys(self.mids)
        length = 0
        for mid in self.mids:
            totals = self.database.get_totals(mid)
            total_ups, total_downs = zip(*totals)
            mid_data[mid] = (total_ups, total_downs)
            if len(total_ups) > length:
                length = len(total_ups)
            if len(total_downs) > length:
                length = len(total_downs)
        print("Writing data totals to file")
        """ Write to file """
        with open(os.path.join(self.working_directory, "mids_data_up.dat"), 'w') as up_file:
            with open(os.path.join(self.working_directory, "mids_data_down.dat"), 'w') as down_file:
                for mid in self.mids:
                    total_ups = mid_data[mid][0]
                    total_downs = mid_data[mid][1]
                    for i in range(0, length):
                        if i < len(total_ups):
                            up_file.write(str(total_ups[i]))
                            down_file.write(str(total_downs[i]))
                        else:
                            up_file.write("na")
                            down_file.write("na")
                        # Write character separator.
                        if i != length - 1:
                            up_file.write("\t")
                            down_file.write("\t")
                    up_file.write("\n")
                    down_file.write("\n")

    class MockDispersy:

        class MockMember:

            def __init__(self, mid):
                # Return the mid with 0 appended so that the pk has the same length.
                # The real pk cannot be retrieved.
                self.public_key = mid + '0'*(PK_LENGTH - len(mid))

        def __init__(self):
            return

        def get_member(self, mid=''):
            return self.MockMember(mid)


class SingleDatabaseReader(DatabaseReader):

    def __init__(self, working_directory):
        super(SingleDatabaseReader, self).__init__(working_directory)

    def get_database(self, db_path):
        return MultiChainExperimentAnalysisDatabase(self.MockDispersy(), os.path.join(db_path, "multichain/1/"))

    def generate_graph(self):
        # Read all nodes
        print "Reading Database"
        ids = self.database.get_ids()
        for block_id in ids:
            block = self.database.get_by_block_id(block_id)
            # Fix the block. The hash is different because the Public Key is not accessible.
            block.id = block_id
            self.add_block_to_graph(block_id, block)
        self._work_empty_hash()
        self._work_genesis_hash()
        self._write_graph()


class GumbyIntegratedDatabaseReader(DatabaseReader):

    def __init__(self, working_directory):
        super(GumbyIntegratedDatabaseReader, self).__init__(working_directory)

    def generate_graph(self):
        print "Reading databases."
        databases = []
        for dir_name in os.listdir(self.working_directory):
            # Read all nodes
            if 'Tribler' in dir_name:
                databases.append(MultiChainDB(self.MockDispersy(), path.join(self.working_directory, dir_name)))
                ids = databases[-1].get_ids()
                for block_id in ids:
                    block = databases[-1].get_by_block_id(block_id)
                    # Fix the block. The hash is different because the Public Key is not accessible.
                    block.id = block_id
                    self.add_block_to_graph(block_id, block)
                    if not self.database.contains(block.id):
                        self.database.add_block(block)
        self._work_empty_hash()
        self._work_genesis_hash()
        self._write_graph()

    def get_database(self, db_path):
        return MultiChainExperimentAnalysisDatabase(self.MockDispersy(), db_path)


class GumbyStandaloneDatabaseReader(DatabaseReader):

    def __init__(self, working_directory):
        super(GumbyStandaloneDatabaseReader, self).__init__(working_directory)

    def generate_graph(self):
        print "Reading databases."
        databases = []
        for dir_name in os.listdir(self.working_directory):
            # Read all nodes
            if string_is_int(dir_name):
                databases.append(MultiChainDB(self.MockDispersy(), path.join(self.working_directory, dir_name)))
                ids = databases[-1].get_ids()
                for block_id in ids:
                    block = databases[-1].get_by_block_id(block_id)
                    # Fix the block. The hash is different because the Public Key is not accessible.
                    block.id = block_id
                    self.add_block_to_graph(block_id, block)
                    if not self.database.contains(block.id):
                        self.database.add_block(block)
        self._work_empty_hash()
        self._work_genesis_hash()
        self._write_graph()

    def get_database(self, db_path):
        return MultiChainExperimentAnalysisDatabase(self.MockDispersy(), db_path)


def string_is_int(string):
    try:
        int(string)
        return True
    except ValueError:
        return False