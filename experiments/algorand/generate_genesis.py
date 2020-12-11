import json

NUM_VALIDATORS = 4

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

stake_per_node = round(100 / NUM_VALIDATORS, 3)
last_node_stake = stake_per_node + 100 - (stake_per_node * NUM_VALIDATORS)

for node_ind in range(NUM_VALIDATORS):
    wallet_name = "Wallet%d" % (node_ind + 1)
    stake = stake_per_node if node_ind != (NUM_VALIDATORS - 1) else last_node_stake

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

with open("genesis.json", "w") as genesis_file:
    genesis_file.write(json.dumps(genesis))
