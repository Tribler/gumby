import random

from pony.orm import db_session

from tribler.core.components.knowledge.community import knowledge_community
from tribler.core.components.knowledge.community.knowledge_community import KnowledgeCommunity
from tribler.core.components.knowledge.community.knowledge_payload import StatementOperation
from tribler.core.components.knowledge.db.knowledge_db import Operation, ResourceType
from tribler.core.components.knowledge.knowledge_component import KnowledgeComponent

from gumby.experiment import experiment_callback
from gumby.modules.tribler_module import TriblerBasedModule
from gumby.util import run_task


def random_infohash():
    """ Generates a random torrent infohash string """
    return ''.join(random.choice('0123456789abcdef') for _ in range(40))


class KnowledgeModule(TriblerBasedModule):
    """
    This module contains code to manage experiments with the Knowledge component.
    """

    def on_id_received(self):
        super().on_id_received()
        tribler_config = self.tribler_module.tribler_config
        tribler_config.knowledge.enabled = True

        # We want to gossip knowledge immediately after creating it
        knowledge_community.TIME_DELTA_READY_TO_GOSSIP = {'minutes': 0}

        self.autoplot_create('num_statements', 'num_statements')

    def on_ipv8_available(self, ipv8):
        super().on_ipv8_available(ipv8)
        run_task(self.write_knowledge_statistics, interval=5, delay=0)

    @experiment_callback
    def generate_knowledge(self):
        """
        Generate a knowledge graph and add it to the database.
        """
        for _ in range(100):
            self.create_random_statement()

    @db_session
    def create_random_statement(self):
        public_key = self.community.key.pub().key_to_bin()
        infohash = random_infohash()
        operation = StatementOperation(subject_type=ResourceType.TORRENT, subject=infohash,
                                       predicate=ResourceType.TAG,
                                       object="test", operation=Operation.ADD, clock=0,
                                       creator_public_key=public_key)
        operation.clock = self.community.db.get_clock(operation) + 1
        signature = self.community.sign(operation)
        self.community.db.add_operation(operation, signature, is_local_peer=True)

    def write_knowledge_statistics(self):
        with db_session:
            statements = self.community.db.instance.Statement.select().count()
            self.autoplot_add_point("num_statements", statements)

    @property
    def community(self) -> KnowledgeCommunity:
        return self.get_component(KnowledgeComponent).community
