import asyncio
import json
import os
import subprocess
import time
from threading import Thread

from ruamel.yaml import YAML, RoundTripDumper, round_trip_dump
from ruamel.yaml.comments import CommentedMap
from twisted.internet import reactor
from twisted.internet.task import LoopingCall, deferLater

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module, ExperimentModule

from hfc.fabric import Client


@static_module
class HyperledgerModule(ExperimentModule):
    """
    Note: for Hyperledger, we are doing some special stuff with initiating transactions.
    Therefore, this class does not extend from BlockchainModule.
    """

    def __init__(self, experiment):
        super(HyperledgerModule, self).__init__(experiment)
        self.config_path = "/home/pouwelse/hyperledger-network-template"
        self.monitor_process = None
        self.fabric_client = None
        self.num_validators = int(os.environ["NUM_VALIDATORS"])
        self.num_clients = int(os.environ["NUM_CLIENTS"])
        self.tx_rate = int(os.environ["TX_RATE"])
        self.did_write_start_time = False
        self.spawner = None

    def is_client(self):
        my_peer_id = self.experiment.scenario_runner._peernumber
        return my_peer_id > self.num_validators

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
    def generate_client_config(self):
        my_peer_id = self.experiment.scenario_runner._peernumber

        # Generate network.json which specifies the necessary information for the client.
        with open(os.path.join(self.config_path, "network-template.json"), "r") as network_template_file:
            network_config = json.loads(network_template_file.read())

        network_config["client"]["credentialStore"]["path"] = "/tmp/hfc-kvs-%d" % my_peer_id
        network_config["client"]["credentialStore"]["cryptoStore"]["path"] = "/tmp/hfc-kvs-%d" % my_peer_id

        # Fill in 'organizations'
        for organization_index in range(1, self.num_validators + 1):
            # Get the PK filename
            keystore_path = os.path.join(self.config_path, "crypto-config/peerOrganizations/org%d.example.com/users/Admin@org%d.example.com/msp/keystore" % (organization_index, organization_index))
            pk_file_path = os.listdir(keystore_path)[0]

            info = {
                "mspid": "Org%dMSP" % organization_index,
                "peers": ["peer0.org%d.example.com" % organization_index],
                "users": {
                    "Admin": {
                        "cert": os.path.join(self.config_path, "crypto-config/peerOrganizations/org%d.example.com/users/Admin@org%d.example.com/msp/signcerts/Admin@org%d.example.com-cert.pem" %
                                (organization_index, organization_index, organization_index)),
                        "private_key": os.path.join(keystore_path, pk_file_path)
                    }
                }
            }
            network_config["organizations"]["org%d.example.com" % organization_index] = info

        # Fill in 'orderers'
        for orderer_index in range(1, self.num_validators + 1):
            orderer_port = (7050 + 1000 * (orderer_index - 1))
            host, _ = self.experiment.get_peer_ip_port_by_id(orderer_index)
            info = {
                "url": "%s:%d" % (host, orderer_port),
                "grpcOptions": {
                    "grpc.ssl_target_name_override": "orderer%d.example.com" % orderer_index,
                    "grpc-max-send-message-length": 15
                },
                "tlsCACerts": {
                    "path": os.path.join(self.config_path, "crypto-config/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem")
                }
            }
            network_config["orderers"]["orderer%d.example.com" % orderer_index] = info

        # Fill in 'peers'
        for peer_index in range(1, self.num_validators + 1):
            peer_port = (7051 + 1000 * (peer_index - 1))
            host, _ = self.experiment.get_peer_ip_port_by_id(peer_index)
            info = {
                "url": "%s:%d" % (host, peer_port),
                "grpcOptions": {
                    "grpc.ssl_target_name_override": "peer0.org%d.example.com" % peer_index,
                    "grpc.http2.keepalive_time": 15
                },
                "tlsCACerts": {
                    "path": os.path.join(self.config_path, "crypto-config/peerOrganizations/org%d.example.com/peers/peer0.org%d.example.com/msp/tlscacerts/tlsca.org%d.example.com-cert.pem" % (peer_index, peer_index, peer_index))
                }
            }
            network_config["peers"]["peer0.org%d.example.com" % peer_index] = info

        with open("network.json", "w") as network_file:
            network_file.write(json.dumps(network_config))

    @experiment_callback
    def generate_artifacts(self):
        self._logger.info("Generating artifacts...")
        os.system("/home/pouwelse/hyperledger-network-template/generate.sh")

    @experiment_callback
    def start_network(self):
        if self.is_client():
            return

        self._logger.info("Starting network...")
        my_peer_id = self.experiment.scenario_runner._peernumber
        os.system("/home/pouwelse/hyperledger-network-template/start_containers.sh %d" % my_peer_id)

    @experiment_callback
    def deploy_chaincode(self):
        """
        Create the channel, add peers and instantiate chaincode.
        """
        self._logger.info("Deploying chaincode...")
        network_file_path = os.path.join(os.getcwd(), "network.json")
        channel_config_path = os.path.join(self.config_path, "channel-artifacts", "channel.tx")
        cmd = "python /home/pouwelse/hyperledger-network-template/scripts/deploy.py %s %s > deploy.out 2>&1" % (network_file_path, channel_config_path)
        my_env = os.environ.copy()
        my_env["GOPATH"] = "/home/pouwelse/gocode"
        subprocess.Popen(cmd, env=my_env, shell=True)

    @experiment_callback
    def stop_network(self):
        if self.is_client():
            return

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
    def print_block(self):
        loop = asyncio.get_event_loop()
        org1_admin = self.fabric_client.get_user(org_name='org1.example.com', name='Admin')

        # Query Block by block number
        response = loop.run_until_complete(self.fabric_client.query_block(
            requestor=org1_admin,
            channel_name='mychannel',
            peers=['peer0.org1.example.com'],
            block_number='1',
            decode=True
        ))
        print(response)

    @experiment_callback
    def print_chain_info(self):
        loop = asyncio.get_event_loop()
        org1_admin = self.fabric_client.get_user(org_name='org1.example.com', name='Admin')

        # Query Block by block number
        response = loop.run_until_complete(self.fabric_client.query_info(
            requestor=org1_admin,
            channel_name='mychannel',
            peers=['peer0.org1.example.com'],
            decode=True
        ))
        print(response)

    @experiment_callback
    def stop_monitor(self):
        """
        Stop monitoring the blocks.
        """
        self._logger.info("Stopping monitor...")
        if self.monitor_process:
            self.monitor_process.kill()

    @experiment_callback
    def start_client(self):
        if not self.is_client():
            return

        self.fabric_client = Client(net_profile="network.json")

    @experiment_callback
    def start_creating_transactions(self, duration):
        self.start_creating_transactions_with_rate(self.tx_rate, float(duration))

    @experiment_callback
    def start_creating_transactions_with_rate(self, tx_rate, duration):
        """
        Start with submitting transactions.
        """
        if not self.is_client():
            return

        duration = float(duration)

        if not self.did_write_start_time:
            # Write the start time to a file
            submit_tx_start_time = int(round(time.time() * 1000))
            with open("submit_tx_start_time.txt", "w") as out_file:
                out_file.write("%d" % submit_tx_start_time)
            self.did_write_start_time = True

        individual_tx_rate = int(tx_rate) / self.num_clients
        my_peer_id = self.experiment.scenario_runner._peernumber

        # Spawn the process
        script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tx_spawner.py")
        cmd = "python %s network.json %d %d %d %d %f > spawner.out 2>&1" % (script_path, individual_tx_rate, self.num_clients, self.num_validators, my_peer_id, duration)
        self.spawner = subprocess.Popen(cmd, shell=True)

    @experiment_callback
    def stop(self):
        print("Stopping Hyperledger...")
        reactor.stop()
