Advanced Gumby Experiments and Scenarios
========================================

In the previous tutorial, we have shown how to run a simple experiment with Gumby. Gumby spawned two instances that
run independently from each other. Most of the time, however, you want more control over the actions performed during
your experiment. In this tutorial, we will setup a more advanced experiment. Our experiment will spawn five instances
that are time-synchronized with each other. After five seconds, each instance will write its ID to a file. When the
experiment ends, we will sum up all these instance IDs and write it to a file.

Configuration file
------------------

Our configuration file will look as follows:

.. literalinclude:: synchronized_instances.conf

Most of the configuration options should be familiar at this point. We annotated two new configuration options, namely
``sync_port`` and ``scenario_file``. We further explain the effect of these configuration options.

Scenario Files
--------------

Note that we specify a scenario file in our configuration file. A scenario file is a file that contains all events
during our experiment. Each event includes a time when the event should fire, and a reference to a Python method.
The scenario file is a very convenient way of building an experiment, and can quickly be reused.
For example, a scenario file can contain a particular workload that the system should process.
The scenario file used in our experiment looks as follows:

.. literalinclude:: write_ids.scenario

The first two lines specify which modules to include.
We will explain experiment modules later in this tutorial.
For now, we will focus on the two events that are specified in this scenario file:

.. code-block:: none

   @0:5 write_peer_id
   @0:9 stop

The above two events are scheduled to fire after five and nine seconds after experiment start, respectively.
The first event calls the ``write_peer_id`` method that simply writes the ID of the instance, or peer, to a file.
Specifically, each Gumby instance is assigned a unique ID, starting from 1.
The ``write_peer_id`` method is defined in the ``SimpleModule`` class in the ``simple_module.py`` file.
This Python code is imported in the first line of our scenario file.
The ``stop`` method is implemented in the ``ExperimentModule`` class, which is the superclass of ``SimpleModule``.

By default, an event will be executed by all peers. One can restrict which instances run a particular event. For
example, the line below specifies that only peer 2 writes its peer ID:

.. code-block:: none

   @0:5 write_peer_id {2}

Experiment Modules
------------------

Gumby enables experiment designers to provide their functionality in separate modules.
In the experiment described in this tutorial, we import the ``SimpleModule`` class in our experiment, which has the
following content:

.. literalinclude:: simple_module.py

This file contains the definition of the ``SimpleModule`` class.
The class contains a single method, namely ``write_peer_id``.
This method simply writes the ID of the peer to a file named ``id.txt``.
Note that the name of this method corresponds to the event specified in our scenario file, and this method is invoked
when the event fires. The method is annotated with a ``experiment_callback`` decorator. This is required to correctly
connect the event in the scenario file and the logic in the module.

An experiment can also import multiple modules.
Gumby automatically imports these module on runtime and registers the events to the available callbacks.
This allows re-use of experiment logic across different experiments.

Instance Synchronization
------------------------

Each spawned instance independently executes the scenario file.
This makes it important that each instance starts roughly at the same time.
Gumby includes a synchronization server that prepares peers for the experiment, assigns IDs, and makes sure that peers
start execution of the scenario file roughly at the same time.
This synchronization process is coordinated by Gumby automatically.
Recall that, in contrast to the previous experiment, we do not set the ``experiment_server_cmd`` configuration option
to blank.
This ensures that Gumby will spawn a synchronization server.
The ``sync_host`` option specifies the IP address or host name of the machine running the synchronization server.
In this experiment we set it to localhost.
The ``sync_port`` option in the configuration file specifies the port of the synchronization server, and indicates to
which port the spawned clients should connect. A value of ``__unique_port__`` indicates that Gumby will pick a random
free port on runtime.

Post-experiment Data Aggregation
--------------------------------

We now focus on the post-experiment script.
This post-experiment script is executed after the scenario file is finished and reads all written peer IDs and sums
them.
Note that in the configuration file, we specify to run the ``post_process_write_ids.sh`` bash script, which looks
as follows:

.. literalinclude:: post_process_write_ids.sh

This simple script first executes the ``post_process_write_ids.py`` file and then calls the
``graph_process_guard_data.sh`` script to plot the graphs. The content of the ``post_process_write_ids.py`` file is
as follows:

.. literalinclude:: post_process_write_ids.py

This Python file defines the ``IDStatisticsParser`` class which is a subclass of ``StatisticsParser``.
The latter class provides basic functionality to quickly aggregate data generated by peers.
Of particular interest is the ``yield_files`` method that returns an iterator with files created by experiment peers
that match a particular pattern.
In the ``aggregate_peer_ids`` method we iterate through all the files named ``id.txt``, read them, and aggregate the
integer value included in these files.
Then the result is written to the ``sum_id.txt`` file.

Running the Experiment
----------------------

You can run the experiment with the following command:

.. code-block:: bash

   $ gumby/run.py gumby/docs/tutorials/synchronized_instances.conf

This will execute the experiment described above.
You should see something similar to the log lines below:

.. code-block:: none

   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:23,644:INFO:1 of 5 expected subscribers connected.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:26,639:INFO:2 of 5 expected subscribers connected.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,645:INFO:4 of 5 expected subscribers connected.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,646:INFO:All subscribers connected!
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,646:INFO:1 of 5 expected subscribers ready.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,649:INFO:All subscribers are ready, pushing data!
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,649:INFO:Pushing a 359 bytes long json doc.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,649:INFO:1 of 5 expected subscribers received the data.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,649:INFO:Data sent to all subscribers, giving the go signal in 1.0 secs.
   INFO:ProcessRunner:[] ERR: 2021-07-17 17:55:27,650:INFO:Starting the experiment!

These log lines indicate that the spawned instances are connecting with the synchronization server and that the
experiment starts only after all instances have an ID assigned and are synchronized.

A file named ``sum_id.txt`` should have been created in the experiment output directory. This file should contain the
value 15, which corresponds to the sum of the IDs of all participating peers (1+2+3+4+5). Note that Gumby also creates
sub-directories to store particular files created by individual peers. The directory name corresponds with the peer ID.
These sub-directories should contain the ``id.txt`` file, created by the ``write_peer_id`` method.

This tutorial covere more advanced concepts of Gumby, and shows how one can setup advanced experiments using scenario
files and experiment modules. In the next tutorial, we show how to deploy and execute the above experiment on the DAS5
supercomputer.