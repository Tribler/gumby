import json
import os
from os import path
import base64

from Tribler.community.trustchain.database import TrustChainDB


class TrustChainExperimentAnalysisDatabase(TrustChainDB):
    """
    Extended TrustChainDB that provides additional functionality to analyze an experiment.
    """

    def __init__(self, working_directory):
        super(TrustChainExperimentAnalysisDatabase, self).__init__(working_directory, "trustchain")

    def get_all_blocks(self):
        """
        Returns all blocks form the database
        """
        return self._getall(u"LIMIT ?", (-1,))


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

    def generate_block_file(self):
        print "Writing TrustChain records to file"
        with open(os.path.join(self.working_directory, "trustchain.dat"), 'w') as trustchain_file:
            # Write header
            trustchain_file.write(
                "tx public_key sequence_number link_public_key link_sequence_number previous_hash signature hash\n"
            )

            # Write blocks
            blocks = self.database.get_all_blocks()
            for block in blocks:
                trustchain_file.write(
                    json.dumps(block.transaction) + " " +
                    base64.encodestring(block.public_key).replace('\n', '').replace('\r', '') + " " +
                    str(block.sequence_number) + " " +
                    base64.encodestring(block.link_public_key).replace('\n', '').replace('\r', '') + " " +
                    str(block.link_sequence_number) + " " +
                    base64.encodestring(block.previous_hash).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.signature).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.hash).replace('\n', '').replace('\r', '') + " " +
                    "\n"
                )


class GumbyDatabaseAggregator(DatabaseReader):

    def get_database(self, db_path):
        return TrustChainExperimentAnalysisDatabase(db_path)

    def combine_databases(self):
        print "Reading databases"
        total_blocks = 0
        for node_dir_name in os.listdir(path.join(self.working_directory, "localhost")):
            for mod_dir_name in os.listdir(path.join(self.working_directory, "localhost", node_dir_name)):
                # Read all nodes
                if mod_dir_name.startswith(".TriblerModule"):
                    db_path = path.join(self.working_directory, "localhost", node_dir_name, mod_dir_name)
                    print "Considering database %s" % db_path
                    database = TrustChainExperimentAnalysisDatabase(db_path)
                    for block in database.get_all_blocks():
                        if not self.database.contains(block):
                            self.database.add_block(block)
                            total_blocks += 1
        print "Found %d unique trustchain (half) blocks across databases" % total_blocks
