import csv
import heapq
import time
from binascii import hexlify

import networkx as nx
from six.moves import xrange

from ipv8.attestation.trustchain.block import TrustChainBlock, EMPTY_PK

KEY_LEN = 8


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
        self.known_connections = nx.Graph()

        self.claim_proofs = {}
        self.nonces = {}

        self.block_time = {}
        self.block_file = None

    def key_to_id(self, key):
        return str(hexlify(key)[-KEY_LEN:])[2:-1]

    def id_to_int(self, id):
        return int(id, 16)

    def int_to_id(self, int_val):
        val = hex(int_val)[2:]
        while len(val) < KEY_LEN:
            val = "0" + val
        return val

    def add_connections(self, peer_a, peer_b):
        self.known_connections.add_edge(peer_a, peer_b)

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
        self.block_time[(block.public_key, block.sequence_number)] = int(round(time.time() * 1000))

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
                                     spend_num=spend.sequence_number)
        elif 'spend_num' not in self.work_graph[id_from][id_to] or \
                self.work_graph[id_from][id_to]["spend_num"] < spend.sequence_number:
            self.work_graph[id_from][id_to]["spend_num"] = spend.sequence_number

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
                                     spend_num=claim.link_sequence_number,
                                     claim_num=claim.sequence_number,
                                     claim_key=claim.public_key)
        elif 'claim_num' not in self.work_graph[id_from][id_to] or \
                self.work_graph[id_from][id_to]["claim_num"] < claim.sequence_number:
            self.work_graph[id_from][id_to]["claim_num"] = claim.sequence_number
            self.work_graph[id_from][id_to]["claim_key"] = claim.public_key

        if 'verified' not in self.work_graph[id_from][id_to]:
            self.work_graph[id_from][id_to]['verified'] = False

        if lpk == EMPTY_PK or (not self.work_graph[id_from][id_to]['verified'] and
                               self.get_balance(id_from, True) >= 0):
            self.work_graph[id_from][id_to]['verified'] = True
            # self.update_claim_proof(id_to, id_from)
            self.update_chain_dependency(id_to)

    def update_claim_proof(self, peer_a, peer_b):
        """
        Add proven claim relationship peer_a - peer_b
        :param peer_a: Claimer
        :param peer_b: Spender
        """
        if peer_a not in self.claim_proofs:
            self.claim_proofs[peer_a] = []
        heapq.heappush(self.claim_proofs[peer_a], (-self.work_graph[peer_b][peer_a]['total_spend'], peer_b))

    def update_chain_dependency(self, peer_id):
        if self.get_balance(peer_id, verified=True) >= 0:
            next_vals = []
            for k in self.work_graph.successors(peer_id):
                if 'verified' in self.work_graph[peer_id][k] and not self.work_graph[peer_id][k]['verified']:
                    self.work_graph[peer_id][k]['verified'] = True
                    # self.update_claim_proof(k, peer_id)
                    next_vals.append(k)
            for k in next_vals:
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

    def get_new_peer_nonce(self, peer_pk):
        peer_id = self.key_to_id(peer_pk)
        if peer_id not in self.nonces:
            self.nonces[peer_id] = '1'
        else:
            self.nonces[peer_id] = str(int(self.nonces[peer_id]) + 1)
        return self.nonces[peer_id]

    def get_peer_status(self, public_key):
        peer_id = self.key_to_id(public_key)
        status = {}
        if peer_id not in self.work_graph:
            return status
        # Get all spends
        status['spends'] = {}
        for v in self.work_graph.successors(peer_id):
            status['spends'][v] = self.get_total_pairwise_spends(peer_id, v)
        status['claims'] = {}
        for v in self.work_graph.predecessors(peer_id):
            status['claims'][v] = self.get_total_pairwise_spends(v, peer_id)
        status['seq_num'] = self.get_latest(public_key).sequence_number
        return status

    def get_total_claims(self, peer_id, only_verified=True):
        if peer_id not in self.work_graph:
            # Peer not known
            return 0
        return sum(self.work_graph[k][peer_id]['total_spend'] for k in self.work_graph.predecessors(peer_id)
                   if self.is_verified(k, peer_id) or not only_verified)

    def _construct_path_id(self, path):
        res_id = ""
        res_id = res_id + str(len(path))
        for k in path[1:-1]:
            res_id = res_id + str(k[-3:-1])
        val = self.work_graph[path[-2]][path[-1]]["total_spend"]
        res_id = res_id + "{0:.2f}".format(val)
        return res_id

    def get_known_chains(self, peer_id):
        return (k[0] for k in self.get_peer_chain(peer_id))

    def add_peer_proofs(self, peer_id, seq_num, status, proofs):
        if peer_id not in self.claim_proofs or self.claim_proofs[peer_id][0] < seq_num:
            self.claim_proofs[peer_id] = (seq_num, status, proofs)

    def get_peer_proofs(self, peer_id, seq_num):
        if peer_id not in self.claim_proofs or seq_num > self.claim_proofs[peer_id][0]:
            return None
        return self.claim_proofs[peer_id]

    def get_last_seq_num(self, peer_id):
        if peer_id not in self.claim_proofs:
            return 0
        else:
            return self.claim_proofs[peer_id][0]

    def dump_peer_status(self, peer_id, status):
        if 'spends' not in status or 'claims' not in status:
            # Status is illformed
            return False

        for (p, v) in status['spends'].items():
            self.work_graph.add_edge(peer_id, p,
                                     total_spend=float(v),
                                     verified=True,
                                     spend_num=status['seq_num'])

        for p, v in status['claims'].items():
            self.work_graph.add_edge(p, peer_id,
                                     total_spend=float(v),
                                     verified=True,
                                     claim_num=status['seq_num'])
        self.update_chain_dependency(peer_id)
        return True

    def get_peer_chain(self, peer_id, seq_num=None, pack_except=set()):
        """
        Get minimum claims that can cover the spends of peer_id at seq_num

        :param peer_id:
        :param seq_num:
        :param pack_except:
        """
        genesis = self.key_to_id(EMPTY_PK)
        spends = self.get_total_spends(peer_id)
        vals = []
        while self.work_graph.has_node(genesis) and self.work_graph.has_node(peer_id) and spends > 0:
            proofs = []
            values = []
            v = heapq.heappop(self.claim_proofs[peer_id])
            vals.append(v)
            spends += v[0]
            proofs.append(v[1])
            values.append(v[0])
            if v[1] != genesis:
                # get the proofs for the peer
                add_proofs = self.get_peer_chain(v[1])
                for p, v in add_proofs:
                    proofs.extend(p)
                    values.extend(v)
            yield (proofs)
        if len(vals) > 0:
            self.claim_proofs[peer_id] = list(heapq.merge(self.claim_proofs[peer_id], vals))

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
        if not self.work_graph.has_edge(a_id, b_id) or 'claim_num' not in self.work_graph[a_id][b_id]:
            return None
        else:
            blk = self.get(self.work_graph[a_id][b_id]['claim_key'], self.work_graph[a_id][b_id]['claim_num'])
            return self.get_linked(blk), blk

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

    def commit_block_times(self):
        with open(self.block_file, "a") as t_file:
            writer = csv.DictWriter(t_file, ['time', 'transaction', 'type', "seq_num", "link", 'from_id', 'to_id'])
            for block_id in self.block_time:
                block = self.block_cache[block_id]
                time = self.block_time[block_id]
                from_id = str(hexlify(block.public_key)[-8:])[2:-1]
                to_id = str(hexlify(block.link_public_key)[-8:])[2:-1]
                writer.writerow({"time": time, 'transaction': str(block.transaction),
                                 'type': block.type.decode(),
                                 'seq_num': block.sequence_number, "link": block.link_sequence_number,
                                 'from_id': from_id, 'to_id': to_id
                                 })
            self.block_time.clear()

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
