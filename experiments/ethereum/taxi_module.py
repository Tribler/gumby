import time

from experiments.ethereum.ethereum_module import EthereumModule
from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule

from web3 import Web3


@static_module
class TaxiModule(ExperimentModule):

    def __init__(self, experiment):
        super(TaxiModule, self).__init__(experiment)
        self.market_contract = None
        self.w3 = None

    def get_ethereum_module(self):
        for module in self.experiment.experiment_modules:
            if isinstance(module, EthereumModule):
                return module

        return None

    def get_market_contract(self):
        if not self.market_contract:
            # Find the Ethereum module to fetch the address/ABI of the deployed contract
            found = False
            for module in self.experiment.experiment_modules:
                if isinstance(module, EthereumModule):
                    self._logger.info("Found Ethereum module!")
                    url = 'http://localhost:%d' % (14000 + self.experiment.my_id)
                    self.w3 = Web3(Web3.HTTPProvider(url))
                    self.market_contract = self.w3.eth.contract(address=module.deployed_contract_address,
                                                                abi=module.deployed_contract_abi)
                    found = True
                    break

            if not found:
                self._logger.error("Ethereum module not found!")

        return self.w3, self.market_contract

    @experiment_callback
    def ride_offer(self, x, y, order_id=None):
        w3, market_contract = self.get_market_contract()
        if not market_contract:
            self._logger.warning("Market contract not found!")
            return

        submit_time = int(round(time.time() * 1000))
        eth_module = self.get_ethereum_module()
        if eth_module:
            eth_module.submitted_transactions.append((order_id, submit_time))

        market_contract.functions.offerRide(int(order_id), int(x), int(y)).transact(
            {"gas": 1000000, "from": w3.eth.accounts[0]})

    @experiment_callback
    def ride_request(self, x, y, order_id=None):
        w3, market_contract = self.get_market_contract()
        if not market_contract:
            self._logger.warning("Market contract not found!")
            return

        submit_time = int(round(time.time() * 1000))
        eth_module = self.get_ethereum_module()
        if eth_module:
            eth_module.submitted_transactions.append((order_id, submit_time))

        market_contract.functions.requestRide(int(order_id), int(x), int(y)).transact({"from": w3.eth.accounts[0]})
