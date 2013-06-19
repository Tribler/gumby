gumby
=====

Experiment runner framework for Dispersy and Tribler


## Framework components ##

### run.py ###

Experiment entry point, must receive an experiment config file as argument.

### experiment config file ###

It contains all the settings needed to run an experiment using this framework.
See the example.conf file for more info.

### run_in_env.sh ###

Shell script to run commands inside the experiment environment. Enabling virtualenv if necessary, loading all the needed variables, etc.
Automatically used to run the scripts called by run.py specified on the config file.

### run-tracker.sh ###

Looks for an unused UDP port, updates the settings with the port number and starts the tracker.
