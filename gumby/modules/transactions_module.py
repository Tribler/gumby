import os
import time

from twisted.internet import reactor
from twisted.internet.task import LoopingCall, deferLater

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule


@static_module
class TransactionsModule(ExperimentModule):

    def __init__(self, experiment):
        super(TransactionsModule, self).__init__(experiment)

        self.num_validators = int(os.environ["NUM_VALIDATORS"])
        self.num_clients = int(os.environ["NUM_CLIENTS"])
        self.tx_rate = int(os.environ["TX_RATE"])
        self.tx_lc = None
        self.did_write_start_time = False
        self.transfer = None

    def on_all_vars_received(self):
        super(TransactionsModule, self).on_all_vars_received()

        # Make sure that the number of validators + the number of clients is the number of total instances
        if self.num_validators + self.num_clients != len(self.all_vars.keys()):
            self._logger.error("Number of validators (%d) + number of clients (%d) unequal to num instances (%d)!",
                               self.num_validators, self.num_clients, len(self.all_vars.keys()))
            self.stop()

    def is_client(self):
        my_peer_id = self.experiment.scenario_runner._peernumber
        return my_peer_id > self.num_validators

    @experiment_callback
    def start_creating_transactions(self):
        self.start_creating_transactions_with_rate(self.tx_rate)

    @experiment_callback
    def start_creating_transactions_with_rate(self, tx_rate):
        """
        Start with submitting transactions.
        """
        if not self.is_client():
            return

        if self.tx_lc:
            self.tx_lc.stop()
            self.tx_lc = None

        if not self.did_write_start_time:
            # Write the start time to a file
            submit_tx_start_time = int(round(time.time() * 1000))
            with open("submit_tx_start_time.txt", "w") as out_file:
                out_file.write("%d" % submit_tx_start_time)
            self.did_write_start_time = True

        self._logger.info("Starting transactions...")
        self.tx_lc = LoopingCall(self.transfer)

        # Depending on the tx rate and number of clients, wait a bit
        individual_tx_rate = int(tx_rate) / self.num_clients
        self._logger.info("Individual tx rate: %f" % individual_tx_rate)

        def start_lc():
            self._logger.info("Starting tx lc...")
            self.tx_lc.start(1.0 / individual_tx_rate)

        my_peer_id = self.experiment.scenario_runner._peernumber
        my_client_id = my_peer_id - self.num_validators
        deferLater(reactor, (1.0 / self.num_clients) * (my_client_id - 1), start_lc)

    @experiment_callback
    def stop_creating_transactions(self):
        """
        Stop with submitting transactions.
        """
        if not self.is_client():
            return

        self._logger.info("Stopping transactions...")
        self.tx_lc.stop()
        self.tx_lc = None
