import os

from gumby.modules.experiment_module import static_module, ExperimentModule
from gumby.modules.transactions_module import TransactionsModule


@static_module
class BlockchainModule(ExperimentModule):

    def __init__(self, experiment):
        super(BlockchainModule, self).__init__(experiment)

        self.num_validators = int(os.environ["NUM_VALIDATORS"])
        self.num_clients = int(os.environ["NUM_CLIENTS"])
        self.tx_rate = int(os.environ["TX_RATE"])
        self.transactions_manager = None

    def is_client(self):
        my_peer_id = self.experiment.scenario_runner._peernumber
        return my_peer_id > self.num_validators

    def on_all_vars_received(self):
        super(BlockchainModule, self).on_all_vars_received()

        # Find the transactions manager and set it
        for module in self.experiment.experiment_modules:
            if isinstance(module, TransactionsModule):
                self._logger.info("Found transaction manager!")
                self.transactions_manager = module
