Gumby
=====

An experiment runner framework to run local and distributed experiments.
Gumby allows developers and scientists to design complex experiments and run them on the DAS5 supercomputer.

Notable features:
- Run IPv8/Tribler experiments with thousands of instances in a local or remote (DAS5) environment.
- A built-in experiment coordinator, facilitating coordination and message passing between any running instance.
- Scenario files to schedule custom actions during an experiment run.
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

## Tutorials
A tutorial for creating your first Gumby experiment is available [here](docs/tutorials/experiment_tutorial_1.rst).
