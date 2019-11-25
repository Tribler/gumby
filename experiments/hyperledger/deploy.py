import asyncio
import sys
import time

from hfc.fabric import Client


def run(network_file_path):
    loop = asyncio.get_event_loop()
    cli = Client(net_profile=network_file_path)

    org1_admin = cli.get_user(org_name='org1.example.com', name='Admin')
    chaincode_version = 'v5'

    # Create a New Channel, the response should be true if succeed
    response = loop.run_until_complete(cli.channel_create(
        orderer='orderer1.example.com',
        channel_name='mychannel',
        requestor=org1_admin,
        config_tx='channel-artifacts/channel.tx'
    ))
    print("Result of channel creation: %s" % response)

    time.sleep(2)

    # Join Peers into Channel
    for peer_index in range(1, len(cli.peers) + 1):
        admin = cli.get_user(org_name='org%d.example.com' % peer_index, name='Admin')
        responses = loop.run_until_complete(cli.channel_join(
            requestor=admin,
            channel_name='mychannel',
            peers=['peer0.org%d.example.com' % peer_index],
            orderer='orderer%d.example.com' % peer_index,
        ))
        print("Results of channel join: %s" % responses)

    # Install chaincode
    for peer_index in range(1, len(cli.peers) + 1):
        admin = cli.get_user(org_name='org%d.example.com' % peer_index, name='Admin')
        responses = loop.run_until_complete(cli.chaincode_install(
            requestor=admin,
            peers=['peer0.org%d.example.com' % peer_index],
            cc_path='github.com/chaincode/sacc',
            cc_name='sacc',
            cc_version=chaincode_version,
        ))
        print("Result of chaincode install: %s" % responses)

    # Instantiate chaincode
    response = loop.run_until_complete(cli.chaincode_instantiate(
        requestor=org1_admin,
        channel_name='mychannel',
        peers=['peer0.org1.example.com'],
        args={"Args": ["john", "0"]},
        cc_name='sacc',
        cc_version=chaincode_version,
        wait_for_event=True  # optional, for being sure chaincode is instantiated
    ))
    print("Result of chaincode instantiation: %s" % response)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Require network.json file as argument!")
        exit(1)
    run(sys.argv[1])
