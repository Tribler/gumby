The purpose of this document is to showcase creation of a basic Gumby experiment.
This document assumes the reader has a basic understanding of creating Dispersy communities (see `Dispersy <http://dispersy.readthedocs.io/en/devel/>`_).

*************************
My first Gumby experiment
*************************

Generally, Gumby experiments consist of three files (which will be explained in the following sections):

- A ``.conf`` file to construct a runtime for your experiment
- A ``.py`` file to provide functionality for your experiment
- A ``.scenario`` to orchestrate events for your experiment

Throughout this document we will present a running example for you to follow.
To start the example off, we will create a new folder:

``gumby/experiments/hello_world/``

This folder will house the aforementioned files (``hello_world.conf``, ``hello_world_module.py`` and ``hello_world.scenario``).
Also, don't forget an ``__init__.py`` file.

The configuration file
----------------------

The entry point for your experiment is the configuration (``.conf``) file.
Configuration files mainly fall into one of the two following categories:

- Local experiments
- DAS5 experiments

In our example, we are keeping it simple and we will use the following ``hello_world.conf`` file to run a local experiment:

.. code-block:: None

    ## hello_world.conf ##
    
    # The name for our experiment (cosmetic only)
    experiment_name = "hello_world"
    
    # The time before we automatically hard-kill this experiment
    experiment_time = 90
    
    # The amount of processes we wish to deploy, this should be reflected in local_instance_cmd
    sync_subscribers_amount = 5

    # This command will launch a process for each launch_scenario.py you feed it
    local_instance_cmd = "process_guard.py -c launch_scenario.py -c launch_scenario.py -c launch_scenario.py -c launch_scenario.py -c launch_scenario.py -t $EXPERIMENT_TIME -m $OUTPUT_DIR  -o $OUTPUT_DIR "
    
    # The scenario file to run
    scenario_file = 'hello_world.scenario'

    ## Don't change the following settings, unless you are 100% sure you know what you are doing

    # Run a Dispersy tracker for peer discovery
    tracker_cmd = 'run_tracker.sh'
    tracker_port = __unique_port__

    # The experiment setup script to use
    experiment_server_cmd = 'experiment_server.py'
    
    # The designated experiment synchronization peer
    sync_host = 127.0.0.1
    sync_port = __unique_port__
    
    # How long we should wait for experiment nodes to connect
    sync_experiment_start_delay = 1

    # The command which will handle post processing
    post_process_cmd = 'post_process_dispersy_experiment.sh'

    # Run python in a virtual environment
    use_local_venv = FALSE

Alternatively, if you want to run your first experiment on the DAS5:

.. code-block:: None

    ## hello_world_das5.conf ##
    
    # The name for our experiment (cosmetic only)
    experiment_name = "hello_world"

    # The scenario file to run
    scenario_file = 'hello_world.scenario'
    
    # The amound of physical machines to reserve (never more than 20)
    das4_node_amount = 5
    
    # The amount of processes to run over all nodes
    # These will be evenly mapped over the available nodes (in this case 1 per node)
    das4_instances_to_run = 5
    
    # The time before we automatically hard-kill this experiment
    das4_node_timeout = 90

    ## Don't change the following settings, unless you are 100% sure you know what you are doing

    # The DAS5 deployment scripts
    local_setup_cmd = 'das4_setup.sh'
    local_instance_cmd = 'das4_reserve_and_run.sh'
    das4_node_command = "launch_scenario.py"

    # Run a Dispersy tracker for peer discovery
    tracker_cmd = 'run_tracker.sh'
    tracker_port = __unique_port__

    # The experiment setup script to use
    experiment_server_cmd = 'experiment_server.py'
    
    # The designated experiment synchronization peer's port
    sync_port = __unique_port__
    
    # How long we should wait for experiment nodes to connect
    sync_experiment_start_delay = 1

    # The command which will handle post processing
    post_process_cmd = 'post_process_dispersy_experiment.sh'

    # Run python in a virtual environment
    use_local_venv = TRUE
    
    # Use systemtap (for debugging)
    with_systemtap = false
    
The scenario file
-----------------
Now that we have instructed Gumby how to set up our environment, we can write the file in charge of generating events: the scenario (.scenario) file.
Consider the following ``hello_world.scenario``:

.. code-block:: python

    ## hello_world.scenario ##
    # With this we tell Gumby to load the DispersyModule, which takes care of providing a Dispersy instance for us
    # If you want extended Tribler functionality, you should use gumby.modules.tribler_module.TriblerModule instead
    &module gumby.modules.dispersy_module.DispersyModule
    
    # This tells Gumby to load our hello_world_module.py file's HelloWorldModule class
    &module experiments.hello_world.hello_world_module.HelloWorldModule
    
    # At 0 seconds into the experiment, make sure our HelloWorldCommunity does not communicate with the outside world
    @0 isolate_community HelloWorldCommunity
    
    # At 1 second into the experiment, start running Dispersy
    @1 start_session

    # At 2 seconds into the experiment, introduce all of the peers to each other
    @2 introduce_peers
    
    # At 15 seconds into the experiment, reset our Dispersy statistics
    # And draw a line in our output graphs called `start-experiment`
    @15 reset_dispersy_statistics
    @15 annotate start-experiment
    
    # At 30 seconds into the experiment, call a HelloWorldModule function
    @30 hello
    
    # At 1 minute into the experiment, call a HelloWorldModule function for one process (node 3)
    @1:0 extended_hello 2 {3}
    
    # Once we've had our fun, stop cleanly
    @1:10 stop_session
    @1:15 stop

If you find yourself writing the same statements over and over, you can use ``&include some_other.scenario`` to include the entirety of a different scenario file.
As a final note: the timestamps can go up to hours (``hours:minutes:seconds``), though currently most experiments in Gumby only use seconds.

The module file
---------------

The module file is what provides the functionality for the events generated by the scenario file.
It is common to use the ``_module`` postfix when naming your module python file.
The module code for our running example is given below:

.. code-block:: python
    
    from gumby.experiment import experiment_callback
    from gumby.modules.community_experiment_module import CommunityExperimentModule
    from gumby.modules.community_launcher import CommunityLauncher
    from gumby.modules.experiment_module import static_module
    from gumby.modules.isolated_community_loader import IsolatedCommunityLoader

    from Tribler.dispersy.community import Community
    from Tribler.dispersy.conversion import DefaultConversion


    class HelloWorldCommunityLoader(IsolatedCommunityLoader):
        """
        This provides the capability to run your communities in an isolated fashion.
        You can include multiple launchers here.
        """

        def __init__(self, session_id):
            super(HelloWorldCommunityLoader, self).__init__(session_id)
            self.set_launcher(HelloWorldCommunityLauncher())


    class HelloWorldCommunityLauncher(CommunityLauncher):
        """
        This class forwards all the information Dispersy needs to launch our community.
        """
        def get_community_class(self):
            return HelloWorldCommunity

        def get_my_member(self, dispersy, session):
            return dispersy.get_new_member()

        def get_kwargs(self, session):
            return {}


    class HelloWorldCommunity(Community):
        """
        This is the Community we are testing. It does nothing right now.
        """
        def initiate_conversions(self):
            return [DefaultConversion(self)]


    @static_module
    class HelloWorldModule(CommunityExperimentModule):
        """
        This is the module we reference through the scenario (note @static_module).
        All of the functionality we want to expose to the scenario is marked `@experiment_callback`.
        """
        def __init__(self, experiment):
            super(HelloWorldModule, self).__init__(experiment, HelloWorldCommunity)
            self.dispersy_provider.custom_community_loader = HelloWorldCommunityLoader(self.dispersy_provider.session_id)

        @experiment_callback
        def hello(self):
            print "Hello human!"

        @experiment_callback
        def extended_hello(self, repetitions, separator=" "):
            print separator.join(["Hello human!"]*int(repetitions))

Ordinarily one would have his ``@experiment_callback`` actually do something with the loaded community (``self.community``).
For the sake of keeping this example short, these callbacks only perform print statements.
Furthermore, why one isolates Dispersy communities and how the communities are made will also remain outside of the scope of this document.
You can read more about isolation of communities in `the isolation documentation <community_isolation.rst>`_.

You are now ready to run your experiment! You can do so, by running the following command (make sure you followed the README setup instructions correctly):

``gumby/run.py gumby/experiments/hello_world/hello_world.conf``

If you have done everything correctly, this command should run for 1 minute and 15 seconds.
Upon completion, you will find several ``.out`` files in your ``output`` folder.
You will find the output of the ``HelloWorldModule.hello()`` function in all of these files.
Only one node will also have the ``HelloWorldModule.extended_hello()`` output.
