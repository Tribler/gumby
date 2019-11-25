import asyncio
import logging
import sys
import time

from hfc.fabric import Client

logger = logging.getLogger("txspawner")
tx_info = []


async def start_creating_transactions(network_file, tx_rate, num_clients, num_validators, my_peer_id, duration):
    logger.info("Starting to create transactions with tx rate %f, validators %d and my peer %d" % (tx_rate, num_validators, my_peer_id))
    fabric_client = Client(net_profile=network_file)
    loop = asyncio.get_event_loop()
    fabric_client.new_channel('mychannel')
    validator_peer_id = ((my_peer_id - 1) % num_validators) + 1
    logger.info("My validator: %d" % validator_peer_id)
    admin = fabric_client.get_user(org_name='org%d.example.com' % validator_peer_id, name='Admin')

    def stop():
        # Write the transaction info away
        with open("tx_submit_times.txt", "w") as tx_times_file:
            for tx_id, submit_time in tx_info:
                tx_times_file.write("%s,%d\n" % (tx_id, submit_time))

        loop.stop()
        exit(0)

    loop.call_later(duration, stop)

    my_client_id = my_peer_id - num_validators
    initial_delay = (1.0 / num_clients) * (my_client_id - 1)
    await asyncio.sleep(initial_delay)

    while True:
        # Transact...
        logger.info("Initiating transaction...")
        start_time = time.time()
        submit_time = int(round(start_time * 1000))

        # Make a transaction
        args = ["blah", "20"]
        tx_id = await loop.create_task(fabric_client.chaincode_invoke(
            requestor=admin,
            channel_name='mychannel',
            peers=['peer0.org%d.example.com' % validator_peer_id],
            args=args,
            cc_name='sacc',
            fcn='set'
        ))
        if len(tx_id) == 64:
            tx_info.append((tx_id, submit_time))

        duration = time.time() - start_time

        await asyncio.sleep(max(0, 1.0 / tx_rate - duration))


# Argument 1: network file
# Argument 2: tx rate
# Argument 3: num clients
# Argument 3: num validators
# Argument 4: my peer ID
# Argument 5: duration
if __name__ == "__main__":
    if len(sys.argv) < 6:
        logger.info("Wrong number of parameters!")
        exit(1)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_creating_transactions(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])))
