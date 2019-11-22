"""
This script updates the genesis file.
"""
import json
import os

NUM_WITNESSES = 2
NUM_USERS = 100

accounts = []  # List of tuple (brain_priv_key, pub_key, wif_priv_key)

# Read the keys
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "keypairs.txt"), "r") as keys_file:
    lines = keys_file.readlines()
    for ind, line in enumerate(lines):
        if len(line) > 0:
            parts = line.rstrip('\n').split(",")
            accounts.append(parts)

with open("my-genesis-clean.json") as genesis_file:
    content = genesis_file.read()
    json_content = json.loads(content)

json_content["initial_active_witnesses"] = NUM_WITNESSES
json_content["immutable_parameters"]["min_witness_count"] = NUM_WITNESSES - 1

# Write the accounts
for ind in range(NUM_USERS):
    json_content["initial_accounts"].append({
        "name": "user%d" % ind,
        "owner_key": accounts[ind][1],
        "active_key": accounts[ind][1],
        "is_lifetime_member": True
    })

# Write the initial witnesses
for ind in range(NUM_WITNESSES):
    json_content["initial_witness_candidates"].append({
        "owner_name": "user%d" % ind,
        "block_signing_key": accounts[ind][1],
    })

with open("my-genesis.json", "w") as out_genesis_file:
    out_genesis_file.write(json.dumps(json_content, indent=4, separators=(',', ': ')))
