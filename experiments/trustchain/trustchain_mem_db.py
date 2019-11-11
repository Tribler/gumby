from binascii import hexlify

import networkx as nx
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

        self.double_spends = {}
        self.peer_map = {}

        self.work_graph = nx.DiGraph()
        self.known_chains = {}

    def key_to_id(self, key):
        return str(hexlify(key)[-8:])[2:-1]

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
        id_from = self.key_to_id(pk)
        id_to = self.key_to_id(lpk)
        if id_from not in self.work_graph or \
                id_to not in self.work_graph[id_from] or \
                'total_spend' not in self.work_graph[id_from][id_to] or \
                self.work_graph[id_from][id_to]["total_spend"] < float(spend.transaction["total_spend"]):
            self.work_graph.add_edge(id_from, id_to,
                                     total_spend=float(spend.transaction["total_spend"]),
                                     proof={'spend': spend})
        else:
            self.work_graph[id_from][id_to]["proof"]['spend'] = spend

    def add_claim(self, claim):
        pk = claim.public_key
        lpk = claim.link_public_key
        id_from = self.key_to_id(lpk)
        id_to = self.key_to_id(pk)

        if id_from not in self.work_graph or \
                id_to not in self.work_graph[id_from] or \
                'total_spend' not in self.work_graph[id_from][id_to] or \
                self.work_graph[id_from][id_to]["total_spend"] < float(claim.transaction["total_spend"]):
            self.work_graph.add_edge(id_from, id_to,
                                     total_spend=float(claim.transaction["total_spend"]),
                                     proof={'claim': claim})
        else:
            self.work_graph[id_from][id_to]["proof"]['claim'] = claim

        if 'verified' not in self.work_graph[id_from][id_to]:
            self.work_graph[id_from][id_to]['verified'] = False
        if lpk == EMPTY_PK or (not self.work_graph[id_from][id_to]['verified'] and
                               self.get_balance(id_from, True) >= 0):
            self.work_graph[id_from][id_to]['verified'] = True
            self.update_chain_dependency(id_to)

    def update_chain_dependency(self, peer_id):
        if self.get_balance(peer_id, verified=True) >= 0:
            for k in self.work_graph.successors(peer_id):
                self.work_graph[peer_id][k]['verified'] = True
            for k in self.work_graph.successors(peer_id):
                self.update_chain_dependency(k)

    def get_total_pairwise_spends(self, peer_a, peer_b):
        if not self.work_graph.has_edge(peer_a, peer_b):
            return 0
        else:
            return self.work_graph[peer_a][peer_b]["total_spend"]

    def get_total_spends(self, peer_id):
        if peer_id not in self.work_graph:
            return 0
        else:
            return sum(self.work_graph[peer_id][k]["total_spend"] for k in self.work_graph.successors(peer_id))

    def is_verified(self, p1, p2):
        return 'verified' in self.work_graph[p1][p2] and self.work_graph[p1][p2]['verified']

    def get_total_claims(self, peer_id, only_verified=True):
        if peer_id not in self.work_graph:
            # Peer not known
            return 0
        return sum(self.work_graph[k][peer_id]['total_spend'] for k in self.work_graph.predecessors(peer_id)
                   if self.is_verified(k, peer_id) or not only_verified)

    def get_spends_proofs(self, peer_id):
        if not self.work_graph.has_node(peer_id):
            return []
        p = list()
        for v in self.work_graph.successors(peer_id):
            if 'spend' in self.work_graph[peer_id][v]["proof"]:
                p.append(self.work_graph[peer_id][v]["proof"]['spend'])
            else:
                p.append(self.work_graph[peer_id][v]["proof"]['claim'])
        return p

    def get_claims_proofs(self, peer_id):
        if not self.work_graph.has_node(peer_id):
            return []
        claim_set = list()
        for v in self.work_graph.predecessors(peer_id):
            if 'claim' in self.work_graph[v][peer_id]["proof"]:
                claim_set.append(self.work_graph[v][peer_id]['proof']['claim'])
        return claim_set

    def _construct_path_id(self, path):
        res_id = ""
        res_id = res_id + str(len(path))
        for k in path[1:-1]:
            res_id = res_id + str(k[-3:-1])
        val = self.work_graph[path[-2]][path[-1]]["total_spend"]
        res_id = res_id+"{0:.2f}".format(val)
        return res_id

    def get_known_chains(self, peer_id):
        return (k[0] for k in self.get_peer_chain(peer_id))

    def dump_chain(self, peer_id, chain):
        for p in chain:
            path_id = p[0]
            paths = p[1]
            vals = p[2]
            id_from = self.key_to_id(EMPTY_PK)
            for k in range(len(vals)):
                if k == len(vals) - 1:
                    id_to = peer_id
                else:
                    id_to = paths[k]
                self.work_graph.add_edge(id_from, id_to,
                                         total_spend=float(vals[k]),
                                         verified=True)
                id_from = id_to
            self.update_chain_dependency(id_to)

    def get_peer_chain(self, peer_id, seq_num=None, pack_except=set()):
        genesis = self.key_to_id(EMPTY_PK)
        if self.work_graph.has_node(genesis) and self.work_graph.has_node(peer_id):
            for p in nx.all_simple_paths(self.work_graph, genesis, peer_id):
                val_path = []
                last_k = 0
                path_id = self._construct_path_id(p)
                if path_id in pack_except:
                    continue
                for k in p:
                    if last_k == 0:
                        pass
                    else:
                        val_path.append(self.work_graph[last_k][k]['total_spend'])
                    last_k = k
                yield (path_id, p[1:-1], val_path)


    def get_balance(self, peer_id, verified=True):
        # Sum of claims(verified/or not) - Sum of spends(all known)
        return self.get_total_claims(peer_id, only_verified=verified) - self.get_total_spends(peer_id)

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

    def get_last_pairwise_block(self, peer_a, peer_b):
        # get last claim of peer_b by peer_a
        a_id = self.key_to_id(peer_a)
        b_id = self.key_to_id(peer_b)
        if not self.work_graph.has_edge(a_id, b_id) or 'claim' not in self.work_graph[a_id][b_id]['proof']:
            return None
        else:
            blk = self.work_graph[a_id][b_id]['proof']['claim']
            return self.get_linked(blk), self.work_graph[a_id][b_id]['proof']['claim']

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
