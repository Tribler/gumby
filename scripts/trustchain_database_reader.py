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
        print("Reading databases")
        total_blocks = 0
        for node_dir_name in os.listdir(path.join(self.working_directory, "localhost")):
            for mod_dir_name in os.listdir(path.join(self.working_directory, "localhost", node_dir_name)):
                # Read all nodes
                if mod_dir_name.startswith(".TriblerModule"):
                    db_path = path.join(self.working_directory, "localhost", node_dir_name, mod_dir_name)
                    print("Considering database %s" % db_path)
                    database = TrustChainDB(db_path, "trustchain")
                    for block in database.get_all_blocks():
                        if not self.database.contains(block):
                            self.database.add_block(block)
                            total_blocks += 1
        print("Found %d unique trustchain (half) blocks across databases" % total_blocks)
