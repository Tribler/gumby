import time

from experiments.ethereum.ethereum_module import EthereumModule
from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule

from web3 import Web3


class AssetTradingModule(ExperimentModule):

    def __init__(self, experiment):
        super(AssetTradingModule, self).__init__(experiment)
        self.order_id_map = {}
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
    def ask(self, asset1_amount, asset1_type, asset2_amount, asset2_type, order_id=None):
        w3, market_contract = self.get_market_contract()
        if not market_contract:
            self._logger.warning("Market contract not found!")
            return

        stripped_order_id = int(order_id.split(".")[-1])

        submit_time = int(round(time.time() * 1000))
        eth_module = self.get_ethereum_module()
        if eth_module:
            eth_module.submitted_transactions.append((stripped_order_id, submit_time))

        market_contract.functions.offer(stripped_order_id, int(asset1_amount), asset1_type, int(asset2_amount),
                                        asset2_type, 0, False).transact({"gas": 1000000, "from": w3.eth.accounts[0]})

        if order_id:
            self.order_id_map[stripped_order_id] = stripped_order_id

    @experiment_callback
    def bid(self, asset1_amount, asset1_type, asset2_amount, asset2_type, order_id=None):
        w3, market_contract = self.get_market_contract()
        if not market_contract:
            self._logger.warning("Market contract not found!")
            return

        # Since we have to specify an offer, reverse the assets
        stripped_order_id = int(order_id.split(".")[-1])

        submit_time = int(round(time.time() * 1000))
        eth_module = self.get_ethereum_module()
        if eth_module:
            eth_module.submitted_transactions.append((stripped_order_id, submit_time))

        market_contract.functions.offer(stripped_order_id, int(asset2_amount), asset2_type, int(asset1_amount),
                                        asset1_type, 0, False).transact({"gas": 1000000, "from": w3.eth.accounts[0]})

        if order_id:
            self.order_id_map[stripped_order_id] = stripped_order_id

    @experiment_callback
    def cancel(self, order_id):
        stripped_order_id = int(order_id.split(".")[-1])
        if stripped_order_id not in self.order_id_map:
            self._logger.warning("Want to cancel order but order id %s not found!", stripped_order_id)
            return

        w3, market_contract = self.get_market_contract()
        if not market_contract:
            self._logger.warning("Market contract not found!")
            return

        market_contract.functions.cancel(stripped_order_id).transact({"gas": 1000000, "from": w3.eth.accounts[0]})
