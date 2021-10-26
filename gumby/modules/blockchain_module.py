import os

import psutil

from gumby.modules.experiment_module import ExperimentModule
from gumby.modules.transactions_module import TransactionsModule


class BlockchainModule(ExperimentModule):

    def __init__(self, experiment):
        super(BlockchainModule, self).__init__(experiment)

        self.num_validators = int(os.environ["NUM_VALIDATORS"])
        self.num_clients = int(os.environ["NUM_CLIENTS"])
        self.tx_rate = int(os.environ["TX_RATE"])
        self.transactions_manager = None

    def is_client(self):
        return self.my_id > self.num_validators

    def is_responsible_validator(self):
        """
        Return whether this validator is the responsible validator to setup/init databases on this machine.
        This can only be conducted by a single process.
        """
        if self.is_client():
            return False

        my_host, _ = self.experiment.get_peer_ip_port_by_id(self.my_id)

        is_responsible = True
        for peer_id in self.experiment.all_vars.keys():
            if self.experiment.all_vars[peer_id]['host'] == my_host and int(peer_id) < self.my_id:
                is_responsible = False
                break

        return is_responsible

    def on_all_vars_received(self):
        super(BlockchainModule, self).on_all_vars_received()

        # Find the transactions manager and set it
        for module in self.experiment.experiment_modules:
            if isinstance(module, TransactionsModule):
                self._logger.info("Found transaction manager!")
                self.transactions_manager = module

    def kill_process(self, proc_pid):
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
