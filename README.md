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

To create a new experiment config, just run this

```
gumby/scripts/generate_config_file.py gumby/experiments/my_experiment/new_experiment.conf
```

 This will parse all of Gumby resources and create a self-documented config skeleton for you. Open the file and read the
 instructions there.

### Setting everything up to ###

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
