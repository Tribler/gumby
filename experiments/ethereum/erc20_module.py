import random
import string
import time

from web3 import Web3

from experiments.ethereum.ethereum_module import EthereumModule

from gumby.modules.experiment_module import ExperimentModule


class ERC20Module(ExperimentModule):

    def __init__(self, experiment):
        super().__init__(experiment)
        self.contract = None
        self.w3 = None
        self.ethereum_module = None
        self.validator_peer_id = None

    def get_ethereum_module(self):
        for module in self.experiment.experiment_modules:
            if isinstance(module, EthereumModule):
                return module

        return None

    def on_all_vars_received(self):
        super().on_all_vars_received()

        # Set the transfer function
        self.ethereum_module = self.get_ethereum_module()
        self.ethereum_module.transactions_manager.transfer = self.transfer

        self.validator_peer_id = ((self.my_id - 1) % self.ethereum_module.num_validators) + 1
        host, _ = self.experiment.get_peer_ip_port_by_id(self.validator_peer_id)
        url = 'http://%s:%d' % (host, 14000 + self.validator_peer_id)
        self.w3 = Web3(Web3.HTTPProvider(url))

    def transfer(self):
        contract = self.get_contract()
        submit_time = int(round(time.time() * 1000))
        random_id = ''.join(random.choice(string.ascii_uppercase) for _ in range(5))
        self.ethereum_module.submitted_transactions[random_id] = submit_time
        target_address = self.ethereum_module.others_public_keys[
            (self.validator_peer_id % self.ethereum_module.num_validators) + 1]
        contract.functions.transfer(
            Web3.toChecksumAddress("0x" + target_address), 1, random_id).\
            transact({"gas": 1000000, "from": self.w3.eth.accounts[0]})

    def get_contract(self):
        if not self.contract:
            # Find the Ethereum module to fetch the address/ABI of the deployed contract
            found = False
            for module in self.experiment.experiment_modules:
                if isinstance(module, EthereumModule):
                    self._logger.info("Found Ethereum module!")
                    self.contract = self.w3.eth.contract(address=module.deployed_contract_address,
                                                         abi=module.deployed_contract_abi)
                    found = True
                    break

            if not found:
                self._logger.error("Ethereum module not found!")

        return self.contract
