import os
import subprocess
import time

from ruamel.yaml import YAML, RoundTripDumper, round_trip_dump
from ruamel.yaml.comments import CommentedMap
from twisted.internet import reactor

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule


@static_module
class HyperledgerModule(ExperimentModule):
    """
    Note: for Hyperledger, we are doing some special stuff with initiating transactions.
    Therefore, this class does not extend from BlockchainModule.
    """

    def __init__(self, experiment):
        super(HyperledgerModule, self).__init__(experiment)
        self.config_path = "/home/pouwelse/hyperledger-network-template"
        self.num_validators = int(os.environ["NUM_VALIDATORS"])
        self.tx_rate = int(os.environ["TX_RATE"])
        self.tx_lc = None
        self.monitor_process = None
        self.did_write_start_time = False

    @experiment_callback
    def generate_config(self):
        """
        Generate the initial configuration files.
        """
        # Change crypto-config.yaml and add organizations
        yaml = YAML()
        with open(os.path.join(self.config_path, "crypto-config-template.yaml"), "r") as crypto_config_file:
            config = yaml.load(crypto_config_file)

        config["OrdererOrgs"][0]["Specs"] = []
        for orderer_index in range(1, self.num_validators + 1):
            config["OrdererOrgs"][0]["Specs"].append({"Hostname": "orderer%d" % orderer_index})

        config["PeerOrgs"] = []
        for organization_index in range(1, self.num_validators + 1):
            organization_config = {
                "Name": "Org%d" % organization_index,
                "Domain": "org%d.example.com" % organization_index,
                "EnableNodeOUs": True,
                "Template": {
                    "Count": 1
                },
                "Users": {
                    "Count": 1
                }
            }
            config["PeerOrgs"].append(organization_config)

        with open(os.path.join(self.config_path, "crypto-config.yaml"), "w") as crypto_config_file:
            yaml.dump(config, crypto_config_file)

        # Change configtx.yaml
        yaml = YAML()
        with open(os.path.join(self.config_path, "configtx-template.yaml"), "r") as configtx_file:
            config = yaml.load(configtx_file)

        config["Profiles"]["TwoOrgsChannel"]["Application"]["Organizations"] = []
        config["Profiles"]["SampleMultiNodeEtcdRaft"]["Consortiums"]["SampleConsortium"]["Organizations"] = []

        for organization_index in range(1, self.num_validators + 1):
            org_admin = "Org%dMSP.admin" % organization_index
            org_peer = "Org%dMSP.peer" % organization_index
            org_client = "Org%dMSP.client" % organization_index

            organization_config = {
                "Name": "Org%dMSP" % organization_index,
                "ID": "Org%dMSP" % organization_index,
                "MSPDir": "crypto-config/peerOrganizations/org%d.example.com/msp" % organization_index,
                "Policies": {
                    "Readers": {
                        "Type": "Signature",
                        "Rule": "OR('%s', '%s', '%s')" % (org_admin, org_peer, org_client)
                    },
                    "Writers": {
                        "Type": "Signature",
                        "Rule": "OR('%s', '%s')" % (org_admin, org_peer)
                    },
                    "Admins": {
                        "Type": "Signature",
                        "Rule": "OR('%s')" % (org_admin)
                    }
                },
                "AnchorPeers": [{
                    "Host": "peer0.org%d.example.com" % organization_index,
                    "Port": 7050 + organization_index
                }]
            }

            commented_map = CommentedMap(organization_config)
            commented_map.yaml_set_anchor("Org%d" % organization_index, always_dump=True)
            config["Organizations"].append(commented_map)
            config["Profiles"]["TwoOrgsChannel"]["Application"]["Organizations"].append(commented_map)
            config["Profiles"]["SampleMultiNodeEtcdRaft"]["Consortiums"]["SampleConsortium"]["Organizations"].append(commented_map)

        config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["EtcdRaft"]["Consenters"] = []
        config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["Addresses"] = []

        for organization_index in range(1, self.num_validators + 1):
            consenter_port = 7050 + (organization_index - 1) * 1000
            consenter_info = {
                "Host": "orderer%d.example.com" % organization_index,
                "Port": consenter_port,
                "ClientTLSCert": "crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/tls/server.crt" % organization_index,
                "ServerTLSCert": "crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/tls/server.crt" % organization_index
            }
            config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["EtcdRaft"]["Consenters"].append(consenter_info)
            config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["Addresses"].append("orderer%d.example.com:%d" % (organization_index, consenter_port))

        with open(os.path.join(self.config_path, "configtx.yaml"), "w") as configtx_file:
            round_trip_dump(config, configtx_file, Dumper=RoundTripDumper)

        # Determine DNS entries
        extra_hosts = []
        for organization_index in range(1, self.num_validators + 1):
            host, _ = self.experiment.get_peer_ip_port_by_id(organization_index)
            extra_hosts.append("peer0.org%d.example.com:%s" % (organization_index, host))
            extra_hosts.append("orderer%d.example.com:%s" % (organization_index, host))

        # Change docker-composer for orderers
        yaml = YAML()
        with open(os.path.join(self.config_path, "docker-compose-orderers-template.yaml"), "r") as composer_file:
            config = yaml.load(composer_file)

        config["volumes"] = {}
        config["services"] = {}
        for orderer_index in range(1, self.num_validators + 1):
            name = "orderer%d.example.com" % orderer_index
            config["volumes"][name] = None

            orderer_info = {
                "extends": {
                    "file": "base/peer-base.yaml",
                    "service": "orderer-base"
                },
                "container_name": name,
                "networks": ["byfn"],
                "volumes": [
                    "./channel-artifacts/genesis.block:/var/hyperledger/orderer/orderer.genesis.block",
                    "./crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/msp:/var/hyperledger/orderer/msp" % orderer_index,
                    "./crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/tls/:/var/hyperledger/orderer/tls" % orderer_index,
                    "orderer%d.example.com:/var/hyperledger/production/orderer" % orderer_index
                ],
                "ports": ["%d:7050" % (7050 + 1000 * (orderer_index - 1))],
                "extra_hosts": list(extra_hosts)
            }

            config["services"][name] = orderer_info

        with open(os.path.join(self.config_path, "docker-compose-orderers.yaml"), "w") as composer_file:
            yaml.dump(config, composer_file)

        # Change docker-composer for peers
        yaml = YAML()
        with open(os.path.join(self.config_path, "docker-compose-peers-template.yaml"), "r") as composer_file:
            config = yaml.load(composer_file)

        config["volumes"] = {}
        config["services"] = {}
        for organization_index in range(1, self.num_validators + 1):
            name = "peer0.org%d.example.com" % organization_index
            config["volumes"][name] = None

            peer_info = {
                "container_name": name,
                "extends": {
                    "file": "base/peer-base.yaml",
                    "service": "peer-base",
                },
                "environment": [
                    "CORE_PEER_ID=peer0.org%d.example.com" % organization_index,
                    "CORE_PEER_ADDRESS=peer0.org%d.example.com:%d" % (organization_index, 6051 + 1000 * organization_index),
                    "CORE_PEER_LISTENADDRESS=0.0.0.0:%d" % (6051 + 1000 * organization_index),
                    "CORE_PEER_CHAINCODEADDRESS=peer0.org%d.example.com:%d" % (organization_index, 6052 + 1000 * organization_index),
                    "CORE_PEER_CHAINCODELISTENADDRESS=0.0.0.0:%d" % (6052 + 1000 * organization_index),
                    "CORE_PEER_GOSSIP_BOOTSTRAP=peer0.org1.example.com:7051",
                    "CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer0.org1.example.com:7051",
                    "CORE_PEER_LOCALMSPID=Org%dMSP" % organization_index,
                    "CORE_LEDGER_STATE_STATEDATABASE=CouchDB",
                    "CORE_LEDGER_STATE_COUCHDBCONFIG_COUCHDBADDRESS=couchdb%d:5984" % organization_index,
                    "CORE_LEDGER_STATE_COUCHDBCONFIG_USERNAME=",
                    "CORE_LEDGER_STATE_COUCHDBCONFIG_PASSWORD="
                ],
                "volumes": [
                    "/var/run/:/host/var/run/",
                    "./crypto-config/peerOrganizations/org%d.example.com/peers/peer0.org%d.example.com/msp:/etc/hyperledger/fabric/msp" % (organization_index, organization_index),
                    "./crypto-config/peerOrganizations/org%d.example.com/peers/peer0.org%d.example.com/tls:/etc/hyperledger/fabric/tls" % (organization_index, organization_index),
                    "./crypto-config/ordererOrganizations/example.com/orderers:/etc/hyperledger/orderers",
                    "./scripts:/etc/hyperledger/scripts",
                    "peer0.org%d.example.com:/var/hyperledger/production" % organization_index
                ],
                "ports": ["%d:%d" % (6051 + 1000 * organization_index, 6051 + 1000 * organization_index)],
                "networks": ["byfn"],
                "extra_hosts": list(extra_hosts),
                "depends_on": ["couchdb%d" % organization_index]
            }

            config["services"][name] = peer_info

        with open(os.path.join(self.config_path, "docker-compose-peers.yaml"), "w") as composer_file:
            yaml.dump(config, composer_file)

        # Add extra_hosts to docker-composer for cli
        yaml = YAML()
        with open(os.path.join(self.config_path, "docker-compose-cli-template.yaml"), "r") as composer_file:
            config = yaml.load(composer_file)

        config["services"]["cli"]["extra_hosts"] = list(extra_hosts)

        with open(os.path.join(self.config_path, "docker-compose-cli.yaml"), "w") as composer_file:
            yaml.dump(config, composer_file)

        # Change docker-composer for couchdb
        yaml = YAML()
        with open(os.path.join(self.config_path, "docker-compose-couch-template.yaml"), "r") as composer_file:
            config = yaml.load(composer_file)

        config["services"] = {}
        for organization_index in range(1, self.num_validators + 1):
            couch_name = "couchdb%d" % organization_index
            couchdb_info = {
                "container_name": couch_name,
                "image": "hyperledger/fabric-couchdb",
                "environment": [
                    "COUCHDB_USER=",
                    "COUCHDB_PASSWORD="
                ],
                "ports": ["%d:5984" % (5984 + 1000 * (organization_index - 1))],
                "networks": ["byfn"]
            }

            config["services"][couch_name] = couchdb_info

        with open(os.path.join(self.config_path, "docker-compose-couch.yaml"), "w") as composer_file:
            yaml.dump(config, composer_file)

    @experiment_callback
    def generate_artifacts(self):
        self._logger.info("Generating artifacts...")
        os.system("/home/pouwelse/hyperledger-network-template/generate.sh")

    @experiment_callback
    def start_network(self):
        self._logger.info("Starting network...")
        my_peer_id = self.experiment.scenario_runner._peernumber
        os.system("/home/pouwelse/hyperledger-network-template/start_containers.sh %d" % my_peer_id)

    @experiment_callback
    def deploy_chaincode(self):
        """
        Create the channel, add peers and instantiate chaincode.
        """
        self._logger.info("Deploying chaincode...")
        os.system("/home/pouwelse/hyperledger-network-template/deploy.sh %d" % self.num_validators)
        self._logger.info("Chaincode deployed and instantiated!")

    @experiment_callback
    def stop_network(self):
        self._logger.info("Stopping network...")
        os.system("/home/pouwelse/hyperledger-network-template/stop_all.sh")

    @experiment_callback
    def start_monitor(self):
        """
        Start monitoring the blocks
        """
        self._logger.info("Starting monitor...")
        cmd = "cd /home/pouwelse/fabric-examples/fabric-cli/cmd/fabric-cli/ && /home/pouwelse/go/bin/go run /home/pouwelse/fabric-examples/fabric-cli/cmd/fabric-cli/fabric-cli.go event listenblock --cid mychannel --peer localhost:7051 --config /home/pouwelse/fabric-examples/fabric-cli/cmd/fabric-cli/config.yaml > %s" % os.path.join(os.getcwd(), "transactions.txt")
        my_env = os.environ.copy()
        my_env["GOPATH"] = "/home/pouwelse/gocode"
        self.monitor_process = subprocess.Popen(cmd, env=my_env, shell=True)

    @experiment_callback
    def stop_monitor(self):
        """
        Stop monitoring the blocks.
        """
        self._logger.info("Stopping monitor...")
        if self.monitor_process:
            self.monitor_process.kill()

    @experiment_callback
    def start_creating_transactions(self):
        """
        Start with submitting transactions to the peer running on the same server.
        """
        my_peer_id = self.experiment.scenario_runner._peernumber
        tx_rate_client = self.tx_rate / self.num_validators
        sleep_time = 1.0 / tx_rate_client

        if not self.did_write_start_time:
            # Write the start time to a file
            submit_tx_start_time = int(round(time.time() * 1000))
            with open("submit_tx_start_time.txt", "w") as out_file:
                out_file.write("%d" % submit_tx_start_time)
            self.did_write_start_time = True
        
        self._logger.info("Starting transactions (tx rate: %f, sleep time: %f..." % (tx_rate_client, sleep_time))
        cmd = 'docker exec peer0.org%d.example.com bash /etc/hyperledger/scripts/transact.sh %f &' % (my_peer_id, sleep_time)
        subprocess.Popen(cmd, shell=True)

    @experiment_callback
    def transfer(self):
        my_peer_id = self.experiment.scenario_runner._peernumber
        target_organization_id = ((my_peer_id - 1) % self.num_validators) + 1
        cmd = 'docker exec peer0.org%d.example.com peer chaincode invoke -n sacc -c \'{"Args":["set", "a", "20"]}\' -C mychannel -o orderer%d.example.com:7050 --tls true --cafile /etc/hyperledger/orderers/orderer%d.example.com/tls/ca.crt' % (target_organization_id, target_organization_id, target_organization_id)
        subprocess.Popen(cmd, shell=True)

    @experiment_callback
    def stop_creating_transactions(self):
        """
        Stop with submitting transactions.
        """
        self._logger.info("Stopping transactions...")
        my_peer_id = self.experiment.scenario_runner._peernumber
        cmd = 'docker exec peer0.org%d.example.com pkill -f transact' % my_peer_id
        subprocess.Popen(cmd, shell=True)

    @experiment_callback
    def stop(self):
        print("Stopping Hyperledger...")
        reactor.stop()
