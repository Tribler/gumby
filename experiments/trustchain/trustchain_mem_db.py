from six.moves import xrange

from ipv8.attestation.trustchain.block import TrustChainBlock, EMPTY_PK


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

        self.interactions = {}
        self.peer_connections = {}

        self.double_spends = {}
        self.peer_map = {}

    def add_double_spend(self, block1, block2):

        """
        Add information about a double spend to the database.
        """
        self.double_spends[(block1.public_key, block1.sequence_number)] = (block1, block2)

    def get_block_class(self, block_type):
        """
        Get the block class for a specific block type.
        """
        if block_type not in self.block_types:
            return TrustChainBlock

        return self.block_types[block_type]

    def add_peer(self, peer):
        if peer.mid not in self.peer_map:
            self.peer_map[peer.mid] = peer.public_key.key_to_bin()

    def get_latest_peer_block(self, peer_mid):
        if peer_mid in self.peer_map:
            pub_key = self.peer_map[peer_mid]
            return self.get_latest(pub_key)

    def add_block(self, block):
        self.block_cache[(block.public_key, block.sequence_number)] = block
        self.linked_block_cache[(block.link_public_key, block.link_sequence_number)] = block
        if block.public_key not in self.latest_blocks:
            self.latest_blocks[block.public_key] = block
        elif self.latest_blocks[block.public_key].sequence_number < block.sequence_number:
            self.latest_blocks[block.public_key] = block
        if block.type == b"spend":
            self.add_spend(block)
        if block.type == b"claim":
            self.add_claim(block)

    def add_spend(self, spend):
        pk = spend.public_key
        lpk = spend.link_public_key
        if pk not in self.interactions.keys():
            self.interactions[pk] = {}
        if lpk not in self.interactions[pk].keys():
            self.interactions[pk][lpk] = {}
        if 'total_spend' not in self.interactions[pk][lpk] or \
                self.interactions[pk][lpk]["total_spend"] < float(spend.transaction["total_spend"]):
            self.interactions[pk][lpk]["total_spend"] = float(spend.transaction["total_spend"])
            self.interactions[pk][lpk]["block"] = {'spend': spend}
        else:
            self.interactions[pk][lpk]["block"]['spend'] = spend

    def add_claim(self, claim):
        pk = claim.public_key
        lpk = claim.link_public_key
        if lpk not in self.interactions.keys():
            self.interactions[lpk] = {}
        if pk not in self.interactions[lpk].keys():
            self.interactions[lpk][pk] = {}
        if 'total_spend' not in self.interactions[lpk][pk] or \
                self.interactions[lpk][pk]["total_spend"] < float(claim.transaction["total_spend"]):
            self.interactions[lpk][pk]["total_spend"] = float(claim.transaction["total_spend"])
            self.interactions[lpk][pk]["block"] = {'claim': claim}
        else:
            self.interactions[lpk][pk]["block"]['claim'] = claim

        if pk not in self.peer_connections.keys():
            self.peer_connections[pk] = {}

        if lpk not in self.peer_connections[pk]:
            self.peer_connections[pk][lpk] = False
        if lpk == EMPTY_PK or (not self.peer_connections[pk][lpk] and self.get_balance(lpk, True) >= 0):
            self.peer_connections[pk][lpk] = True
            self.update_chain_dependency(pk)

    def update_chain_dependency(self, pk):
        if self.get_balance(pk, verified=True) >= 0:
            if pk not in self.interactions:
                return
            for lpk in self.interactions[pk]:
                self.peer_connections[lpk][pk] = True
            for lpk in self.interactions[pk]:
                self.update_chain_dependency(lpk)

    def get_total_spends(self, pub_key):
        if pub_key not in self.interactions:
            return 0
        else:
            return sum(lpk_val["total_spend"] for pk, lpk_val in self.interactions[pub_key].items())

    def get_specific_spend(self, pub_key, pub_key2):
        if pub_key not in self.interactions or pub_key2 not in self.interactions[pub_key]:
            return 0
        return self.interactions[pub_key][pub_key2]["total_spend"]

    def get_total_claims(self, pub_key, only_verified=True):
        if pub_key not in self.peer_connections:
            # No claim seen by the peer
            return 0
        return sum(self.get_specific_spend(key, pub_key) for key, is_verified in self.peer_connections[pub_key].items()
                   if is_verified or not only_verified)

    def get_spends_proofs(self, pub_key):
        if pub_key not in self.interactions:
            return []
        p = set()
        for v in self.interactions[pub_key].values():
            if 'spend' in self.interactions[pub_key][v]["block"]:
                p.add(self.interactions[pub_key][v]["block"]['spend'])
            else:
                p.add(self.interactions[pub_key][v]["block"]['claim'])
        return p

    def get_claims_proofs(self, pub_key):
        if pub_key not in self.peer_connections:
            return set()
        claim_set = set()
        for lpk in self.peer_connections[pub_key]:
            if lpk in self.interactions and pub_key in self.interactions[lpk] and 'claim' in self.interactions[lpk][pub_key]['block']:
                claim_set.add(self.interactions[lpk][pub_key]['block']['claim'])
        return claim_set

    def get_balance(self, pub_key, verified=True):
        # Sum of claims(verified/or not) - Sum of spends(all known)
        return self.get_total_claims(pub_key, only_verified=verified) - self.get_total_spends(pub_key)

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
        for ind in xrange(1, latest_seq_num + 2):
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
        for seq_num in xrange(start_seq_num, end_seq_num + 1):
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
