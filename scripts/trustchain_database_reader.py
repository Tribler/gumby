from __future__ import print_function

import csv
import os
from os import path

from ipv8.attestation.trustchain.database import TrustChainDB


class DatabaseReader(object):

    def __init__(self, working_directory):
        """
        Parent class that contains functionality for both gumby and single database readers.
        DatabaseReaders process experimentation information.
        """
        # Either contains all information all ready or all information will be aggregated here.
        self.working_directory = working_directory
        self.database = self.get_database(self.working_directory)

    def get_database(self, db_path):
        raise NotImplementedError("Abstract method")

    def combine_databases(self):
        """
        Combines the databases from the different nodes into one local database
        """
        raise NotImplementedError("Abstract method")


class GumbyDatabaseAggregator(DatabaseReader):

    def get_database(self, db_path):
        return TrustChainDB(db_path, "trustchain")

    def combine_databases(self):
        prefix = os.path.join(os.environ['PROJECT_DIR'], 'output')
        postfix = 'database_blocks_'
        block_stat_file = os.path.join(prefix, postfix + "agg.csv")
        print("Reading databases")
        total_blocks = 0
        with open(block_stat_file, "w") as t_file:
            writer = csv.DictWriter(t_file, ['transaction', "seq_num", "link", 'seen_by'])
            writer.writeheader()
            for node_dir_name in os.listdir(path.join(self.working_directory, "localhost")):
                for mod_dir_name in os.listdir(path.join(self.working_directory, "localhost", node_dir_name)):
                    # Read all nodes
                    if mod_dir_name.startswith(".TriblerModule"):
                        db_path = path.join(self.working_directory, "localhost", node_dir_name, mod_dir_name)
                        print("Considering database %s" % db_path)
                        database = TrustChainDB(db_path, "trustchain")
                        peer_index = mod_dir_name.split('-')[2]
                        for block in database.get_all_blocks():
                            writer.writerow(
                                {'transaction': block.transaction, 'seq_num': block.sequence_number,
                                 'link': block.link_sequence_number, 'seen_by': peer_index})
                            if not self.database.contains(block):
                                self.database.add_block(block)
                                total_blocks += 1
            print("Found %d unique trustchain (half) blocks across databases" % total_blocks)
