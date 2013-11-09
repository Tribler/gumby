gumby
=====

Experiment runner framework for Dispersy and Tribler

## Framework components ##

### run.py ###

Experiment entry point, must receive an experiment config file as argument. E.g. after activating the venv using source ~/venv/bin/activate, call ./gumby/run.py gumby/experiments/XYZ/abc.conf

### experiment config file ###

It contains all the settings needed to run an experiment using this framework.

It will usually be stored into experiments/ExperimentName/experiment.conf
If you want to have several variations of the same experiment, store several config files in the experiment dir.

#### Mandatory config params ####

experiment_name: A string that uniquely identifies the experiment. It will be used to create a workspace on the remote nodes.

#### Optional config params ####

TODO

## Directory structure ##

### experiments/ ###

Experiments should go in there, in a folder named after each experiment.
If you want several variations of the same experiment, just create a .conf file for each of them. IE:
 * experiments/MyCrazyExperiment/crazy.conf
 * experiments/MyCrazyExperiment/crazier.conf
 * experiments/MyCrazyExperiment/craziest.conf

If your experiment needs to use a specific script, just store it in this directory, it will be automatically added to PATH.

### legacy_experiments/ ###

Experiments waiting to be ported to gumby

### scripts/ ###

Scripts that can be used as components to build experiments.
If you create a script generic enough to be useful for others, please send a pull request to add it to the collection.

#### Scripts available to use to build experiments ####

##### run_in_env.py #####

Shell script to run commands inside the experiment environment. Enabling virtualenv if necessary, loading all the needed variables, etc.
Automatically used by gumby.

##### run_tracker.sh #####

Looks for an unused UDP port, updates the settings with the port number and starts a dispersy tracker.

##### build_virtualenv.sh #####

Builds a virtualenv with everything necessary to run Tribler/Dispersy. And if dtrace is available in the system, it builds SystemTap and a SystemTap-enabled python 2.7 environment.
Can be safely executed every time the experiment is run as it will detect if the environment is up to date and exit if there's nothing to do.
Be aware that due to SystemTap needing root permissions, the first run of the script will fail giving instructions to the user on how to manually run a couple of commands as root.

TODO: Add missing documentation.

### gumby/ ###

Main gumby package. Where it's core and generic python modules are stored.
