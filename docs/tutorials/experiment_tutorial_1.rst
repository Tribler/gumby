Running a Simple Experiment with Gumby
======================================

In this first tutorial, we will run a very simple experiment using the functionality that Gumby provides.
This experiment is executed locally and spawns two independent CPU-intensive instances (processes) that execute
the ``yes`` command for ten seconds.

The entry point for all Gumby experiments is the configuration (``.conf``) file.
As the name implies, configuration files specify how an experiment is configured.
This configuration is a file containing key and values, and includes an experiment name, the number of instances
being spawned and which command is being executed.
For our first experiment, this configuration file looks as follows:

.. literalinclude:: local_processguard.conf

We annotate each configuration option with a small explanation. Of particular interest is the ``local_instance_cmd``
option. In this experiment, we start the process guard which is a small module that can spawn and monitor subprocesses.
We provide the command that we want each instance to run as argument to the process guard script. the ``-t`` flag
specifies the experiment timeout. When this timeout expires, the spawned instances are terminated. For more information
on the process guard, we refer the reader to the Gumby documentation.

When the experiment ends, the script provided to the ``post_process_cmd`` configuration option will run, if provided.
The ``graph_process_guard_data.sh`` will create graphs from the data collected by the process guard using the R
plotting library.

Note that we set the ``experiment_server_cmd`` option to an empty value. The default way of running Gumby is to spawn
instances that are time-synchronized with each other and can communicate with each other. However, for this simple
tutorial we sidestep this and spawn two independent instances instead.

To run this basic experiment, execute the following command in the directory that contains the ``gumby`` directory:

.. code-block:: bash

   $ gumby/run.py gumby/docs/tutorials/local_processguard.conf

After around ten seconds, the experiment should be done. All experiment artifacts are written to the ``output``
directory. The standard output and standard error streams are written to the ``.out`` and ``.err`` files, respectively.
You should also see the raw monitoring statistics collected by the process guard, and the plotted graphs (the ``.png``
files). The ``utimes.png`` file shows the CPU usage (in user mode) for each spawned instance. Note that process guard
uses the ``procfs`` file system to gather statistics and therefore resource statistics will not be available when the
experiment runs on Mac and/or Windows computers.

That's all for now! By modifying the ``local_instance_cmd`` configuration option, you can run custom commands with
as many instances your experiment requires. In the next tutorial, we will use more advanced concepts of Gumby and show
how to spawn time-synchronized instances and how to work with scenario files.
