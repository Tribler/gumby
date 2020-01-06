Gumby
=====

An experiment runner framework for IPv8 and Tribler.
Gumby allows developers and scientists to devise complex experiments and run them on the DAS5 supercomputer.

Notable features:
- Run IPv8/Tribler experiments with thousands of instances in a local or remote (DAS5) environment.
- Scenario files to schedule actions during an experiment run.
- Resource monitoring (CPU, memory, I/O etc).
- Post-processing functionality to visualize statistics gathered during an experiment with R.

## Installation
Prior to installing Gumby install the required dependencies for basic tests on Ubuntu/debian-based systems by executing the following command:
```
sudo apt-get install python-psutil python-configobj r-base
```

These dependencies can also be installed using `pip`.
Please note that more elaborate experiments might require additional dependencies.

Next, clone this repository from GitHub by running the following command:

```
git clone https://github.com/tribler/gumby
```

## Running your first experiment

The configuration of Gumby experiments are defined by configuration files.
To show how a Gumby experiment is structured and executed, we provide a basic experiment that simply generates some system I/O and plots some metrics.
After cloning the Gumby repository (see above), simply call `gumby/run.py` passing your experiment's config file path as argument.

Example:

```
gumby/run.py gumby/experiments/dummy/local_processguard.conf
```

This will run the experiment, which should take around 15 seconds.
When the experiment terminates, it will plot various system metrics like CPU usage, I/O read and written.
These metrics can be found in the `output` directory, together with various log files.

_when running the experiment for the first time with `ggplot2` installed, it will compile the `ggplot2` R package and its dependencies.
This can take a while to complete._

## Anatomy of an experiment

We now briefly explain how the `local_processguard` experiment that was executed in the previous section, is composed.

#### Configuration file

Each experiment should be defined by a configuration file that contains information about the environment and parameters of the experiment.
The content of the `local_processguard` experiment is shown below:

```
experiment_name = LocalProcessGuard

local_instance_cmd = process_guard.py -c "(yes CPU > /dev/null & find /etc /usr > /dev/null ; wait)" -t 10 -m $OUTPUT_DIR -o $OUTPUT_DIR --network

post_process_cmd = graph_process_guard_data.sh
```

The configuration file defines some keys and values.
Each experiment requires the `experiment_name` variable to be set.
The `local_instance_cmd` describes the command that Gumby should run.
This usually points to an executable file, i.e. a Python file or a script written in bash.
In the example above, it invokes the `process_guard.py` script with a specific command.
The `process_guard.py` script is (another) wrapper around a command and is responsible for monitoring and writing away various statistics of the process, like CPU, memory and I/O usage.
The `post_process_cmd` variable defines an optional script that should be executed *after* the experiment is finished.
The `graph_process_guard_data.sh` scripts reads the statistics as written away by the `process_guard` file, and plots them with R.

This should provide you with a basic understanding of how to run a simple experiment on your local computer.
The remainder of this README will explain more advanced concepts of Gumby.

## Running experiments on the DAS5.

Gumby supports running experiments on the DAS5 supercomputer.
An example configuration file to do so is given below:

```
experiment_name = "simple_das5"

experiment_server_cmd = 'experiment_server.py'

local_setup_cmd = 'das4_setup.sh'

local_instance_cmd = 'das4_reserve_and_run.sh'

# How many nodes do we want? (seconds)
das4_node_amount = 4

# Kill the processes if they don't die after this many seconds
das4_node_timeout = 350

# How many processes do we want to spawn?
das4_instances_to_run = 100

# What command do we want to run on each instance?
das4_node_command = "basic_experiment.py"
```

This configuration file will run a basic experiment on [the DAS5 supercomputer](https://www.cs.vu.nl/das5).
The `das4_response_and_run.sh` script will automatically find a cluster with available nodes and reserve them for the time indicated by `das4_node_timeout`.
The `local_setup_cmd` will prepare the environment on the remote HEAD node.
Note that you can specify the total number of nodes you want to reserve with the `das4_node_amount` variable, and the total instances you want to run with `das4_instances_to_run`.
Each instance executes the `das4_node_command`, (which is `basic_experiment.py` in this experiment).

## Integrating IPv8/Tribler

For specific information on how to use Gumby to run an experiment with IPv8 or Tribler, please have a look at the TrustChain experiment.
The required files for this experiment can be found in the `gumby/experiments/trustchain` directory.

## Scenario files

Often, you want to execute a specific action on one or more running instances, at specified time intervals.
Gumby allows you to specify a scenario file, which describes one or more actions to be executed during the experiment.
An example of the scenario file used during the basic TrustChain experiment is given below:

```
&module gumby.modules.tribler_module.TriblerModule
&module experiments.trustchain.trustchain_module.TrustchainModule

@0:1 isolate_ipv8_overlay TrustChainCommunity
@0:2 start_session
@0:5 init_trustchain
@0:10 introduce_peers max_peers=10
@0:30 annotate start-creating-blocks
@0:30 start_requesting_signatures
@0:90 stop_requesting_signatures
@0:95 write_overlay_statistics
@0:95 write_trustchain_statistics
@0:95 commit_blocks_to_db
@0:100 stop_session
@0:105 stop
```

The scenario file to be used can specified with the `scenario_file` variable in the experiment configuration file.
Note that scenario files are only correctly loaded if you use `launch_scenario.py` as `das4_node_command`.

## Tutorial
A tutorial for creating your first Gumby experiment is availble [here](docs/hello_world.rst).
