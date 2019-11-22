import os

# with open("keypairs.txt", "w") as keys_file:
#     for ind in xrange(3000):
#         with open(os.path.join(os.environ["HOME"], "Documents", "accounts", "user%d.json" % ind), "r") as key_file:
#             content = key_file.read()
#             decoded = json.loads(content)
#             keys_file.write("%s,%s,%s\n" % (decoded['brain_priv_key'], decoded['pub_key'], decoded['wif_priv_key']))


with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "keypairs.txt"), "r") as keys_file:
    lines = keys_file.readlines()
    for ind, line in enumerate(lines):
        if len(line) > 0:
            parts = line.split(",")
            print ind
            print parts[0]
            print parts[1]
