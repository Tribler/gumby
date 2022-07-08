# Gromit Blockchain Benchmarking Tool

This repository contains the code for the Gromit blockchain benchmarking tool.
The tool is based on [an existing experiment framework](https://github.com/tribler/gubmy) and has been modified to 
support the benchmarking of blockchain fabrics. Gromit supports the following blockchain platforms and versions:
- Algorand (v2.3.0)
- Avalanche (v1.1.1)
- Bitshares (v5.0.0)
- Hyperledger Burrow (v0.34.4)
- Ethereum (v1.9.24)
- Hyperledger Fabric (v1.4.9)
- Diem (v1.1.0)
- Stellar (v15.1.0)

All code related to experiments can be found in the `experiments` directory.

## Gromit Architecture

The Gromit architecture overview is visualized below:

TODO: add figure (I already put it in the docs directory, named grom_arch.png)

The orchestrator coordinates the project and communicates with one or more Gromit instances that are running on 
remote servers. We provide below the instructions on how to setup these remote servers, and how to run a particular 
experiment.

## Preparing the environment
Start by cloning this repository from GitHub by running the following command:

```
git clone https://github.com/tribler/gromit
```

On the remote servers, make sure to install the necessary dependencies for the blockchain platform you wish to test.
The required binaries and locations can be found (and changed) by looking at the respective module associated with 
each blockchain platform.
For example, to find the required binaries for Algorand, look at `experiments/algorand/algorand_module.py`.

You can specify 

## Running the experiment

To run a particular experiment, for example, the Ethereum scalability experiment, invoke the following commands from 
the 
orchestrator:

```
export GUMBY_VIRTUALENV_DIR=/home/userattheremoteservers/venv3
export GUMBY_node_timeout=320
export GUMBY_node_amount=4
export GUMBY_NUM_VALIDATORS=128
export GUMBY_NUM_CLIENTS=64
export GUMBY_TX_RATE=40
export GUMBY_SURFNET_SERVERS_FILE="/home/useratorchestrator/servers.txt"

export GUMBY_instances_to_run=$((GUMBY_NUM_VALIDATORS+GUMBY_NUM_CLIENTS))
export GUMBY_SCENARIO_FILE="transfers_short.scenario"
export GUMBY_SCENARIO_DIR="/home/userattheremoteservers/gumby/experiments/ethereum"

export GUMBY_LOG_LEVEL=DEBUG
export GUMBY_PROFILE_MEMORY=FALSE

python3 gumby/run.py gumby/experiments/ethereum/ethereum_experiment.conf
```

Many settings can be changed using environment variables that are prefixed by `GUMBY`, e.g., the number of 
validators, the rate at which transactions are issued, and the scenario to run.
You can specify on which remote servers the experiment should run by specifying a path in the 
`GUMBY_SURFNET_SERVERS_FILE` environment variable. This file contains the IP addresses of the remote servers, one per 
line:

```
139.53.246.193
139.53.246.194
139.53.246.195
139.53.246.196
```

Gromit expects SSH access to the specified servers under a particular user.
To change the SSH user, we suggest to modify the `scripts/surfnet_*.sh` scripts.

## Tutorials
A tutorial that gets you up and running with Gumby is available [here](docs/tutorials/experiment_tutorial_1.rst).

TODO: add citation link