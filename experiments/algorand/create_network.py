"""
Initialize an algorand network with a given number of validator nodes.
"""
import argparse
import json
import os


def create_network(num_validators, root_dir):
    print("Starting to create network info for %d validators in root dir %s..." % (num_validators, root_dir))

    # Step 1: Generate genesis.json, depending on the number of nodes
    genesis = {
        "Genesis": {
            "NetworkName": "",
            "Wallets": [
                # This is filled in
            ]
        },
        "Nodes": [
            # This is filled in
        ]
    }

    stake_per_node = round(100 / num_validators, 3)
    print("Stake per node: %s" % stake_per_node)
    last_node_stake = round(100 - (stake_per_node * num_validators), 3)
    print("Last node stake: %s" % last_node_stake)

    total_stake = 0
    for node_ind in range(num_validators + 1):
        wallet_name = "Wallet%d" % (node_ind + 1)
        stake = stake_per_node if node_ind != (num_validators - 1) else last_node_stake
        total_stake += stake

        wallet_info = {
            "Name": wallet_name,
            "Stake": stake,
            "Online": True
        }
        genesis["Genesis"]["Wallets"].append(wallet_info)

        node_info = {
            "Name": "Node%d" % (node_ind + 1),
            "IsRelay": True,
            "Wallets": [{
                "Name": wallet_name,
                "ParticipationOnly": False
            }]
        }
        genesis["Nodes"].append(node_info)

    print("Total stake: %s" % total_stake)

    with open("genesis.json", "w") as genesis_file:
        genesis_file.write(json.dumps(genesis))

    # Step 2: Create the network/configuration files
    cmd = "goal network create -r %s -n private -t genesis.json" % root_dir
    os.system(cmd)

    # Kill the kmd processes
    cmd = 'pkill -f "kmd-v0.5"'
    os.system(cmd)

    print("Done with making network info!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize an Algorand network.')
    parser.add_argument('--validators', metavar='n', type=int, default=4, help='The number of validators')

    args = parser.parse_args()

    network_path = os.path.join("/tmp", "algo_data_%d" % args.validators)
    if os.path.exists(network_path):
        print("Algorand network already created under %s" % network_path)
    else:
        create_network(args.validators, network_path)
