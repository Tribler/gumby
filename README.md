gumby
=====

Experiment runner framework for Dispersy and Tribler

## How to use it ##

Simply call gumby/run.py passing your config file's path as argument.

Example:

```
gumby/run.py gumby/experiments/dummy/local_prun.conf
```

### Generating a new config file ###

To create a new experiment config, just run this:

```
gumby/scripts/generate_config_file.py gumby/experiments/my_experiment/new_experiment.conf
```

 This will parse all of Gumby resources and create a self-documented config skeleton for you. Open the file and read the
 instructions there.

### Setting everything up to run your experiment ###

Gumby expects the following directory tree:

workspace/: The workspace dir contains everything that the experiment will need during its execution (including Gumby),
it can have whatever name you like.

workspace/gumby/: Here is where you should clone the gumby repo it has to be located in the root of the workspace with
this specific name.

workspace/tribler/: If your experiments use code from tribler, clone the repository in this location so all the helper
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
git clone https://github.com/Tribler/gumby
git clone https://github.com/Tribler/tribler
gumby/run.py gumby/experiments/dispersy/allchannel.conf
ls -R output/
```

## Framework components ##

### run.py ###

Experiment entry point, must receive an experiment config file as argument.

### experiment config file ###

It contains all the settings needed to run an experiment using this framework.

It will usually be stored into experiments/ExperimentName/experiment.conf
If you want to have several variations of the same experiment, store several config files in the experiment dir.

## Directory structure ##

### experiments/ ###

Experiments go in there, in a folder named after each experiment or experiment.
If you want several variations of the same experiment, just create a .conf file for each of them. IE:
 * experiments/my_crazy_experiment/crazy.conf
 * experiments/my_crazy_experiment/crazier.conf
 * experiments/my_crazy_experiment/craziest.conf

If your experiment needs to use a specific script, just store it in this directory, it will be automatically added to
the PATH. (the same goes for PYTHONPATH)

### legacy_experiments/ ###

Experiments waiting to be ported to gumby.

### scripts/ ###

Scripts that can be used as components to build experiments.
If you create a script generic enough to be useful for others, please send a pull request to add it to the collection.

#### Scripts and components available to use to build your experiments ####

Please, check the documentation in the config file template.
