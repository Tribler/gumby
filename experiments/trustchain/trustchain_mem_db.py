from ipv8.attestation.trustchain.block import TrustChainBlock


class TrustchainMemoryDatabase(object):
    """
    This class defines an optimized memory database for TrustChain.
    """

    def __init__(self, working_directory, db_name):
        self.working_directory = working_directory
        self.db_name = db_name
        self.block_cache = {}
        self.linked_block_cache = {}
        self.block_types = {}
        self.latest_blocks = {}
        self.original_db = None

    def get_block_class(self, block_type):
        """
        Get the block class for a specific block type.
        """
        if block_type not in self.block_types:
            return TrustChainBlock

        return self.block_types[block_type]

    def add_block(self, block):
        self.block_cache[(block.public_key, block.sequence_number)] = block
        self.linked_block_cache[(block.link_public_key, block.link_sequence_number)] = block

        if block.public_key not in self.latest_blocks:
            self.latest_blocks[block.public_key] = block
        elif self.latest_blocks[block.public_key].sequence_number < block.sequence_number:
            self.latest_blocks[block.public_key] = block

    def remove_block(self, block):
        self.block_cache.pop((block.public_key, block.sequence_number), None)
        self.linked_block_cache.pop((block.link_public_key, block.link_sequence_number), None)

    def get(self, public_key, sequence_number):
        if (public_key, sequence_number) in self.block_cache:
            return self.block_cache[(public_key, sequence_number)]
        return None

    def get_all_blocks(self):
        return self.block_cache.values()

    def get_number_of_known_blocks(self, public_key=None):
        if public_key:
            return len([pk for pk, _ in self.block_cache.keys() if pk == public_key])
        return len(self.block_cache.keys())

    def contains(self, block):
        return (block.public_key, block.sequence_number) in self.block_cache

    def get_latest(self, public_key, block_type=None):
        # TODO for now we assume block_type is None
        if public_key in self.latest_blocks:
            return self.latest_blocks[public_key]
        return None

    def get_latest_blocks(self, public_key, limit=25, block_types=None):
        latest_block = self.get_latest(public_key)
        if not latest_block:
            return []  # We have no latest blocks

        blocks = [latest_block]
        cur_seq = latest_block.sequence_number - 1
        while cur_seq > 0:
            cur_block = self.get(public_key, cur_seq)
            if cur_block and (not block_types or cur_block.type in block_types):
                blocks.append(cur_block)
                if len(blocks) >= limit:
                    return blocks
            cur_seq -= 1

        return blocks

    def get_block_after(self, block, block_type=None):
        # TODO for now we assume block_type is None
        if (block.public_key, block.sequence_number + 1) in self.block_cache:
            return self.block_cache[(block.public_key, block.sequence_number + 1)]
        return None

    def get_block_before(self, block, block_type=None):
        # TODO for now we assume block_type is None
        if (block.public_key, block.sequence_number - 1) in self.block_cache:
            return self.block_cache[(block.public_key, block.sequence_number - 1)]
        return None

    def get_lowest_sequence_number_unknown(self, public_key):
        if public_key not in self.latest_blocks:
            return 1
        latest_seq_num = self.latest_blocks[public_key].sequence_number
        for ind in range(1, latest_seq_num + 2):
            if (public_key, ind) not in self.block_cache:
                return ind

    def get_lowest_range_unknown(self, public_key):
        lowest_unknown = self.get_lowest_sequence_number_unknown(public_key)
        known_block_nums = [seq_num for pk, seq_num in self.block_cache.keys() if pk == public_key]
        filtered_block_nums = [seq_num for seq_num in known_block_nums if seq_num > lowest_unknown]
        if filtered_block_nums:
            return lowest_unknown, filtered_block_nums[0] - 1
        else:
            return lowest_unknown, lowest_unknown

    def get_linked(self, block):
        if (block.link_public_key, block.link_sequence_number) in self.block_cache:
            return self.block_cache[(block.link_public_key, block.link_sequence_number)]
        if (block.public_key, block.sequence_number) in self.linked_block_cache:
            return self.linked_block_cache[(block.public_key, block.sequence_number)]
        return None

    def crawl(self, public_key, start_seq_num, end_seq_num, limit=100):
        # TODO we assume only ourselves are crawled
        blocks = []
        orig_blocks_added = 0
        for seq_num in range(start_seq_num, end_seq_num + 1):
            if (public_key, seq_num) in self.block_cache:
                block = self.block_cache[(public_key, seq_num)]
                blocks.append(block)
                orig_blocks_added += 1
                linked_block = self.get_linked(block)
                if linked_block:
                    blocks.append(linked_block)

            if orig_blocks_added >= limit:
                break

        return blocks

    def commit(self, my_pub_key):
        """
        Commit all information to the original database.
        """
        if self.original_db:
            my_blocks = [block for block in self.block_cache.values() if block.public_key == my_pub_key]
            for block in my_blocks:
                self.original_db.add_block(block)

    def close(self):
        if self.original_db:
            self.original_db.close()
