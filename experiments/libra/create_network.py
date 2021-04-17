"""
Initialize a Diem network with a given number of validator nodes.
"""
import argparse
import os
import shutil
import signal
import subprocess
from time import sleep

STARTUP_BATCH_SIZE = 2


def create_network(num_validators, root_dir):
    print("Starting to create network info for %d validators in root dir %s..." % (num_validators, root_dir))

    cmd = "/home/jenkins/diem/diem-swarm -n %d --diem-node /this/does/not/exist -c %s 2>&1" % (num_validators, root_dir)
    process = subprocess.Popen([cmd], shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        line = process.stdout.readline()
        if not line:
            break

    print("Done with making network info!")


def initial_node_startup(num_validators):
    print("Starting all nodes...")

    current_node = 0
    while current_node + STARTUP_BATCH_SIZE <= num_validators:
        processes = []
        print("Starting node %d to %d" % (current_node, current_node + STARTUP_BATCH_SIZE - 1))
        for node_index in range(current_node, current_node + STARTUP_BATCH_SIZE):
            cmd = "/home/jenkins/diem/diem-node -f /tmp/diem_data_%d/%d/node.yaml > " \
                  "/tmp/diem_data_%d/logs/%d.log 2>&1" % (num_validators, node_index, num_validators, node_index)
            process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE,  # pylint: disable=W1509
                                       stderr=subprocess.PIPE, preexec_fn=os.setsid)
            processes.append(process)

        sleep(0.5)
        for process in processes:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        current_node += STARTUP_BATCH_SIZE

    # Remove the databases
    for node_id in range(num_validators):
        shutil.rmtree("/tmp/diem_data_%d/%d/db" % (num_validators, node_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize a Diem network.')
    parser.add_argument('--validators', metavar='n', type=int, default=4, help='The number of validators')

    args = parser.parse_args()

    network_path = os.path.join("/tmp", "diem_data_%d" % args.validators)
    if os.path.exists(network_path):
        print("Diem network already created under %s" % network_path)
    else:
        create_network(args.validators, network_path)
        initial_node_startup(args.validators)
