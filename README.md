Gumby
=====

Experiment runner framework for Dispersy and Tribler.

## Dependency Installation ##
To install the required dependencies for basic tests on Ubuntu 15.10, please run the following command.
```
sudo apt-get install python-psutil python-twisted python-configobj r-base
```
For different versions of Linux or Ubuntu, additional dependencies may be required.

For Ubuntu < 15, ggplot2 is also required separately.
```
sudo apt-get install ggplot2
```

Dependencies can also be installed using pip.
```
# on Ubuntu
sudo apt install libssl-dev r-base
# On Fedora
sudo dnf install openssl-devel R

pip install cryptography psutil twisted configobj
```

Please note that more elaborate experiments require additional dependencies, which are specified in the config file.

## How to use it ##

After setting up the workspace (see below), simply call gumby/run.py passing your experiment's config file path as argument.

Example:

```
gumby/run.py gumby/experiments/dummy/local_processguard.conf
```

### Generating a new config file ###

To create a new experiment config, just run this:

```
gumby/scripts/generate_config_file.py gumby/experiments/my_experiment/new_experiment.conf
```

 This will parse all of Gumby resources and create a self-documented config skeleton for you. Open the file and read the
 instructions there.

### Experiment execution sequence ###

 * Clear output dir
 * Sync workspace dir with remote nodes
 * Run local and remote setup scripts concurrently (see `local_setup_cmd` and `remote_setup_cmd` config options in your
   config file)
   * If any of them fail, the experiment will be aborted.
 * Start the tracker in the background (optional, see `tracker_cmd`).
   * Spawn the tracker and keep it running during the whole experiment run time.
   * If the tracker dies during the experiment execution, the experiment will be aborted.
   * When the experiment finishes, the tracker will be killed automatically.
 * Start the experiment server in the background (optional, see `experiment_server_cmd`).
   * If the experiment server exits (default behavior after giving the go signal to all the instances) the experiment
     will _not_ be aborted.
 * Start both local and remote process instances in parallel (see `local_instance_cmd` and `remote_instance_cmd`).
 * Wait for all the instances to die.
 * Collect all the data from the remote output dirs.
 * Run the post-process script locally to generate graphs and whatnot (optional, see `post_process_cmd`)

Remember that the output dir will be wiped out at every experiment execution.  If you want to keep the output of several
runs and you aren't using Jenkins or similar, you could run your experiments with something like
`GUMBY_OUTPUT_DIR=$PWD/output_$(date "+%y-%m-%d_%H:%M:%S") ./gumby/run.py gumby/experiments/.......`

### Setting everything up to run your experiment ###

Gumby expects the following directory tree:

workspace/: The workspace dir contains everything that the experiment will need during its execution (including Gumby),
it can be named as you like.

workspace/gumby/: Here is where you should clone the gumby repo, it has to be located in the root of the workspace with
this specific name.

workspace/tribler/: If your experiments use code from Tribler, clone the repository in this location so all the helper
scripts can find it.

workspace/dispersy/: Idem.

workspace/output/: Experiment output location, this directory will be cleared/created automatically whenever the
experiment is started, so take care of copying anything you want to keep before restarting an experiment.

A typical set up/execution session up would look similar to this:

```
ssh das4
cd /var/scratch/$USER
mkdir my_workspace
cd my_workspace
git clone https://github.com/Tribler/gumby.git
git clone https://github.com/Tribler/tribler.git
gumby/run.py gumby/experiments/dispersy/allchannel.conf
ls -R output/
```

## Framework components ##

### run.py ###

Experiment entry point, must receive an experiment config file as only argument.

### Experiment config file ###

It contains all the settings needed to run an experiment using this framework.

It will usually be stored into experiments/ExperimentName/experiment.conf
If you want to have several variations of the same experiment, store several config files in the experiment dir.

## Directory structure ##

(All relative to Gumby's repository root )

### experiments/ ###

Experiments go in there, in a folder named after each experiment or experiment.
If you want several variations of the same experiment, just create a .conf file for each of them. IE:
 * experiments/my_crazy_experiment/crazy.conf
 * experiments/my_crazy_experiment/crazier.conf
 * experiments/my_crazy_experiment/craziest.conf

If your experiment needs to use a custom script, just store it in this directory, it will be automatically added to
the PATH. (the same goes for PYTHONPATH)

### legacy_experiments/ ###

Experiments waiting to be ported to Gumby.

### scripts/ ###

Scripts that can be used as components to build experiments.
If you create a script generic enough to be useful to others, please send a pull request to add it to the collection.

#### Scripts and components available to use to build your experiments ####

Please, check the documentation in the config file template.

## Tutorial ##
A tutorial for creating your first Gumby experiment is availble [here](docs/hello_world.rst).
