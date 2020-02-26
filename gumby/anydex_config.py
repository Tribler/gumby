import os


class AnyDexConfig(object):

    def __init__(self):
        self.config = {
            'general': {
                'state_dir': ''
            },
            'ipv8': {
                'port': 8000,
                'statistics': False
            },
            'market_community': {
                'enabled': True
            },
            'trustchain': {
                'enabled': True,
                'memory_db': True,
                'ec_keypair_filename': ''
            },
            'dht': {
                'enabled': True
            }
        }

    def get_trustchain_enabled(self):
        return self.config['trustchain']['enabled']

    def set_root_state_dir(self, state_dir):
        self.config["general"]["state_dir"] = state_dir

    def get_state_dir(self):
        return self.config["general"]["state_dir"]

    def set_trustchain_keypair_filename(self, keypairfilename):
        self.config['trustchain']['ec_keypair_filename'] = keypairfilename

    def get_trustchain_keypair_filename(self):
        file_name = self.config['trustchain']['ec_keypair_filename']
        if not file_name:
            file_name = os.path.join(self.get_state_dir(), 'ec_multichain.pem')
            self.set_trustchain_keypair_filename(file_name)
        return file_name

    def set_ipv8_port(self, value):
        self.config['ipv8']['port'] = value

    def get_ipv8_port(self):
        return self.config['ipv8']['port']

    def get_market_community_enabled(self):
        return self.config['market_community']['enabled']

    def get_dht_enabled(self):
        return self.config['dht']['enabled']

    def set_dht_enabled(self, value):
        self.config['dht']['enabled'] = value

    def set_ipv8_statistics(self, value):
        self.config['ipv8']['statistics'] = value

    def get_ipv8_statistics(self):
        return self.config['ipv8']['statistics']

    def set_trustchain_memory_db(self, value):
        self.config['trustchain']['memory_db'] = value

    def use_trustchain_memory_db(self):
        return self.config['trustchain']['memory_db']
