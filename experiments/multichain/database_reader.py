import os
from os import path
import base64

from Tribler.community.multichain.database import MultiChainDB


class MultiChainExperimentAnalysisDatabase(MultiChainDB):
    """
    Extended MultiChainDB that provides additional functionality to analyze an experiment.
    """

    def __init__(self, dispersy, working_directory):
        super(MultiChainExperimentAnalysisDatabase, self).__init__(dispersy, working_directory)

    def get_all_blocks(self):
        """
        Returns all blocks form the database
        """
        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM `multi_chain`"
        db_result = self.execute(db_query).fetchall()
        return [self._create_database_block(result) for result in db_result]


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

    def generate_graph(self):
        """
        Generates a png file of the graph.
        """
        raise NotImplementedError("Abstract method")

    def generate_block_file(self):
        print "Writing multichain to file"
        with open(os.path.join(self.working_directory, "multichain.dat"), 'w') as multichain_file:
            # Write header
            multichain_file.write(
                "public_key_requester "
                "public_key_responder "
                "up "
                "down "

                "total_up_requester "
                "total_down_requester "
                "sequence_number_requester "
                "previous_hash_requester "
                "signature_requester "
                "hash_requester "

                "total_up_responder "
                "total_down_responder "
                "sequence_number_responder "
                "previous_hash_responder "
                "signature_responder "
                "hash_responder\n"
            )

            # Write blocks
            blocks = self.database.get_all_blocks()
            for block in blocks:
                multichain_file.write(
                    base64.encodestring(block.public_key_requester).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.public_key_responder).replace('\n', '').replace('\r', '') + " " +
                    str(block.up) + " " +
                    str(block.down) + " " +

                    str(block.total_up_requester) + " " +
                    str(block.total_down_requester) + " " +
                    str(block.sequence_number_requester) + " " +
                    base64.encodestring(block.previous_hash_requester).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.signature_requester).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.hash_requester).replace('\n', '').replace('\r', '') + " " +

                    str(block.total_up_responder) + " " +
                    str(block.total_down_responder) + " " +
                    str(block.sequence_number_responder) + " " +
                    base64.encodestring(block.previous_hash_responder).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.signature_responder).replace('\n', '').replace('\r', '') + " " +
                    base64.encodestring(block.hash_responder).replace('\n', '').replace('\r', '') + " " +
                    "\n"
                )


class GumbyDatabaseAggregator(DatabaseReader):

    def get_database(self, db_path):
        return MultiChainExperimentAnalysisDatabase(None, db_path)

    def combine_databases(self):
        print "Reading databases"
        databases = []
        for dir_name in os.listdir(self.working_directory):
            # Read all nodes
            if dir_name.startswith(".Tribler"):
                databases.append(MultiChainDB(None, path.join(self.working_directory, dir_name)))
        for database in databases:
            hashes_requester = database.get_all_hash_requester()
            for hash_requester in hashes_requester:
                block = database.get_by_hash_requester(hash_requester)
                if not self.database.contains(hash_requester):
                    self.database.add_block(block)
        total_blocks = len(self.database.get_all_hash_requester())
        print "Found " + str(total_blocks) + " unique multichain blocks across databases"
