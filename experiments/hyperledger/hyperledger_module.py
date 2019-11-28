import asyncio
import json
import os
import shutil
import subprocess
import time

from ruamel.yaml import YAML, RoundTripDumper, round_trip_dump
from ruamel.yaml.comments import CommentedMap
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

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
        self.peer_process = None
        self.orderer_process = None
        self.spawner = None
        self.monitor_lc = None
        self.latest_block_num = 0
        self.block_confirm_times = {}

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
            orderer_host, _ = self.experiment.get_peer_ip_port_by_id(orderer_index)
            config["OrdererOrgs"][0]["Specs"].append({
                "Hostname": "orderer%d" % orderer_index,
                "SANS": [orderer_host]
            })

        config["PeerOrgs"] = []
        for organization_index in range(1, self.num_validators + 1):
            organization_host, _ = self.experiment.get_peer_ip_port_by_id(organization_index)
            organization_config = {
                "Name": "Org%d" % organization_index,
                "Domain": "org%d.example.com" % organization_index,
                "EnableNodeOUs": True,
                "Template": {
                    "Count": 1,
                    "SANS": [organization_host]
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
            organization_host, _ = self.experiment.get_peer_ip_port_by_id(organization_index)

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
                    "Host": organization_host,
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
            organization_host, _ = self.experiment.get_peer_ip_port_by_id(organization_index)
            consenter_port = 7050 + (organization_index - 1) * 1000
            consenter_info = {
                "Host": organization_host,
                "Port": consenter_port,
                "ClientTLSCert": "crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/tls/server.crt" % organization_index,
                "ServerTLSCert": "crypto-config/ordererOrganizations/example.com/orderers/orderer%d.example.com/tls/server.crt" % organization_index
            }
            config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["EtcdRaft"]["Consenters"].append(consenter_info)
            config["Profiles"]["SampleMultiNodeEtcdRaft"]["Orderer"]["Addresses"].append("%s:%d" % (organization_host, consenter_port))

        with open(os.path.join(self.config_path, "configtx.yaml"), "w") as configtx_file:
            round_trip_dump(config, configtx_file, Dumper=RoundTripDumper)

    @experiment_callback
    def init_config(self):
        """
        Initialize the data directories.
        """
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber

        os.mkdir("peer_data")
        os.mkdir("orderer_data")

        shutil.copyfile(os.path.join(self.config_path, "core.yaml"), os.path.join("peer_data", "core.yaml"))
        shutil.copyfile(os.path.join(self.config_path, "core.yaml"), os.path.join("orderer_data", "core.yaml"))
        shutil.copyfile(os.path.join(self.config_path, "orderer.yaml"), os.path.join("orderer_data", "orderer.yaml"))

        # Copy the orderer directory
        orderer_data_path = os.path.join(self.config_path, "crypto-config", "ordererOrganizations", "example.com", "orderers", "orderer%d.example.com" % my_peer_id)
        shutil.copytree(os.path.join(orderer_data_path, "msp"), os.path.join("orderer_data", "msp"))
        shutil.copytree(os.path.join(orderer_data_path, "tls"), os.path.join("orderer_data", "tls"))

        # Copy the peer directory
        peer_data_path = os.path.join(self.config_path, "crypto-config", "peerOrganizations", "org%d.example.com" % my_peer_id, "peers", "peer0.org%d.example.com" % my_peer_id)
        shutil.copytree(os.path.join(peer_data_path, "msp"), os.path.join("peer_data", "msp"))
        shutil.copytree(os.path.join(peer_data_path, "tls"), os.path.join("peer_data", "tls"))

        # Change paths in peer/orderer files
        yaml = YAML()
        with open(os.path.join("peer_data", "core.yaml"), "r") as core_config_file:
            config = yaml.load(core_config_file)

        config["peer"]["fileSystemPath"] = os.path.join(os.getcwd(), "peer_data")

        with open(os.path.join("peer_data", "core.yaml"), "w") as core_config_file:
            yaml.dump(config, core_config_file)

        yaml = YAML()
        with open(os.path.join("orderer_data", "orderer.yaml"), "r") as orderer_config_file:
            config = yaml.load(orderer_config_file)

        config["FileLedger"]["Location"] = os.path.join(os.getcwd(), "orderer_data")
        config["Consensus"]["WALDir"] = os.path.join(os.getcwd(), "orderer_data", "etcdraft", "wal")
        config["Consensus"]["SnapDir"] = os.path.join(os.getcwd(), "orderer_data", "etcdraft", "snapshot")

        with open(os.path.join("orderer_data", "orderer.yaml"), "w") as orderer_config_file:
            yaml.dump(config, orderer_config_file)

    @experiment_callback
    def start_orderers(self):
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber

        orderer_data_path = os.path.join(os.getcwd(), "orderer_data")
        orderer_tls_dir = os.path.join(orderer_data_path, "tls")
        orderer_port = (7050 + 1000 * (my_peer_id - 1))

        orderer_env = os.environ.copy()
        orderer_vars = {
            "FABRIC_CFG_PATH": orderer_data_path,
            "FABRIC_LOGGING_SPEC": "INFO",
            "ORDERER_GENERAL_GENESISMETHOD": "file",
            "ORDERER_GENERAL_LISTENADDRESS": "0.0.0.0",
            "ORDERER_GENERAL_LISTENPORT": "%d" % orderer_port,
            "ORDERER_GENERAL_LOCALMSPID": "OrdererMSP",
            "ORDERER_GENERAL_GENESISFILE": os.path.join(self.config_path, "channel-artifacts", "genesis.block"),
            "ORDERER_GENERAL_LOCALMSPDIR": os.path.join(orderer_data_path, "msp"),

            # TLS
            "ORDERER_GENERAL_TLS_ENABLED": "true",
            "ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY": os.path.join(orderer_tls_dir, "server.key"),
            "ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE": os.path.join(orderer_tls_dir, "server.crt"),
            "ORDERER_GENERAL_CLUSTER_ROOTCAS": "[%s]" % os.path.join(orderer_tls_dir, "ca.crt"),
            "ORDERER_GENERAL_TLS_CERTIFICATE": os.path.join(orderer_tls_dir, "server.crt"),
            "ORDERER_GENERAL_TLS_PRIVATEKEY": os.path.join(orderer_tls_dir, "server.key"),
            "ORDERER_GENERAL_TLS_ROOTCAS": "[%s]" % os.path.join(orderer_tls_dir, "ca.crt")
        }
        orderer_env.update(orderer_vars)

        # Start the orderer
        cmd = "orderer > orderer.out 2>&1"
        self.orderer_process = subprocess.Popen([cmd], shell=True, env=orderer_env)

    @experiment_callback
    def start_peers(self):
        if self.is_client():
            return

        my_peer_id = self.experiment.scenario_runner._peernumber
        host, _ = self.experiment.get_peer_ip_port_by_id(my_peer_id)

        peer_data_path = os.path.join(os.getcwd(), "peer_data")
        peer_tls_dir = os.path.join(peer_data_path, "tls")

        peer_port = (7051 + 1000 * (my_peer_id - 1))
        chaincode_listen_port = 9000 + my_peer_id

        peer_env = os.environ.copy()
        peer_vars = {
            "FABRIC_CFG_PATH": peer_data_path,
            "CORE_PEER_MSPCONFIGPATH": os.path.join(peer_data_path, "msp"),
            "CORE_PEER_LOCALMSPID": "Org%dMSP" % my_peer_id,
            "CORE_PEER_LISTENADDRESS": "0.0.0.0:%d" % peer_port,
            "CORE_PEER_GOSSIP_BOOTSTRAP": "%s:%d" % (host, peer_port),
            "CORE_PEER_ADDRESS" : "%s:%d" % (host, peer_port),
            "CORE_PEER_CHAINCODELISTENADDRESS": "0.0.0.0:%d" % chaincode_listen_port,
            "CORE_PEER_CHAINCODEADDRESS": "%s:%d" % (host, chaincode_listen_port),
            "CORE_PEER_GOSSIP_USELEADERELECTION": "true",
            "CORE_PEER_GOSSIP_EXTERNALENDPOINT": "%s:%d" % (host, peer_port),
            "CORE_PEER_ID": "peer%d" % my_peer_id,
            "CORE_PEER_PROFILE_ENABLED": "true",
            "CORE_PEER_GOSSIP_ORGLEADER": "false",
            "FABRIC_LOGGING_SPEC": "INFO",

            # TLS
            "CORE_PEER_TLS_ENABLED": "true",
            "CORE_PEER_TLS_CERT_FILE": os.path.join(peer_tls_dir, "server.crt"),
            "CORE_PEER_TLS_KEY_FILE": os.path.join(peer_tls_dir, "server.key"),
            "CORE_PEER_TLS_ROOTCERT_FILE": os.path.join(peer_tls_dir, "ca.crt")
        }
        peer_env.update(peer_vars)

        # Start the peer
        cmd = "peer node start > peer.out 2>&1"
        self.peer_process = subprocess.Popen([cmd], shell=True, env=peer_env)

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

        loop = asyncio.get_event_loop()
        self.fabric_client = Client(net_profile=network_file_path)

        org1_admin = self.fabric_client.get_user(org_name='org1.example.com', name='Admin')
        chaincode_version = 'v6'

        # Create a New Channel, the response should be true if succeed
        response = loop.run_until_complete(self.fabric_client.channel_create(
            orderer='orderer1.example.com',
            channel_name='mychannel',
            requestor=org1_admin,
            config_tx=channel_config_path
        ))
        self._logger.info("Result of channel creation: %s", response)

        time.sleep(3)

        # Join Peers into Channel
        for peer_index in range(1, len(self.fabric_client.peers) + 1):
            admin = self.fabric_client.get_user(org_name='org%d.example.com' % peer_index, name='Admin')
            responses = loop.run_until_complete(self.fabric_client.channel_join(
                requestor=admin,
                channel_name='mychannel',
                peers=['peer0.org%d.example.com' % peer_index],
                orderer='orderer%d.example.com' % peer_index,
            ))
            self._logger.info("Results of channel join for peer %d: %s", peer_index, responses)

        # Install chaincode
        for peer_index in range(1, len(self.fabric_client.peers) + 1):
            admin = self.fabric_client.get_user(org_name='org%d.example.com' % peer_index, name='Admin')
            responses = loop.run_until_complete(self.fabric_client.chaincode_install(
                requestor=admin,
                peers=['peer0.org%d.example.com' % peer_index],
                cc_path='github.com/chaincode/sacc',
                cc_name='sacc',
                cc_version=chaincode_version,
            ))
            self._logger.info("Result of chaincode install for peer %d: %s", peer_index, responses)

        # Instantiate chaincode
        response = loop.run_until_complete(self.fabric_client.chaincode_instantiate(
            requestor=org1_admin,
            channel_name='mychannel',
            peers=['peer0.org1.example.com'],
            args={"Args": ["john", "0"]},
            cc_name='sacc',
            cc_version=chaincode_version,
            wait_for_event=True  # optional, for being sure chaincode is instantiated
        ))
        self._logger.info("Result of chaincode instantiation: %s", response)

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

        org1_admin = self.fabric_client.get_user(org_name='org1.example.com', name='Admin')
        loop = asyncio.get_event_loop()

        def get_latest_block_num():
            self._logger.info("Getting latest block nr...")
            response = loop.run_until_complete(self.fabric_client.query_info(
                requestor=org1_admin,
                channel_name='mychannel',
                peers=['peer0.org1.example.com'],
                decode=True
            ))
            print(response)

            latest_block = response.height
            if latest_block > self.latest_block_num:
                self._logger.info("Updating to block nr %d", latest_block)
                confirm_time = int(round(time.time() * 1000))
                for confirmed_block_num in range(self.latest_block_num + 1, latest_block + 1):
                    self.block_confirm_times[confirmed_block_num] = confirm_time

        self.monitor_lc = LoopingCall(get_latest_block_num)
        self.monitor_lc.start(0.1)

    @experiment_callback
    def write_blockchain(self):
        self._logger.info("Writing blockchain...")
        org1_admin = self.fabric_client.get_user(org_name='org1.example.com', name='Admin')
        loop = asyncio.get_event_loop()
        with open("blockchain.txt", "w") as blockchain_file:
            for block_ind in range(1, self.latest_block_num + 1):
                self._logger.info("Getting block %d...", block_ind)
                block = loop.run_until_complete(self.fabric_client.query_block(
                    requestor=org1_admin,
                    channel_name='mychannel',
                    peers=['peer0.org1.example.com'],
                    block_number='1',
                    decode=True
                ))
                blockchain_file.write(json.dumps(block))

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
        if self.monitor_lc:
            self.monitor_lc.stop()
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
        cmd = "python %s network.json %f %d %d %d %f > spawner.out 2>&1" % (script_path, individual_tx_rate, self.num_clients, self.num_validators, my_peer_id, duration)
        self.spawner = subprocess.Popen(cmd, shell=True)

    @experiment_callback
    def stop(self):
        print("Stopping Hyperledger...")
        if self.orderer_process:
            self.orderer_process.kill()
        if self.peer_process:
            self.peer_process.kill()

        reactor.stop()
