The purpose of this document is to show a means of isolating IPv8 overlays from outside interference in Gumby experiments.
This document assumes the reader has a basic understanding of running Gumby experiments, creating IPv8 overlays and running them through the ``TriblerExperimentScriptClient`` class.

*************************************
Isolating and replacing IPv8 overlays
*************************************
As you may have noticed, the overlays loaded by the ``TriblerExperimentScriptClient`` are the live overlays as loaded by Tribler (which you can toggle by setting the correct flags in the ``SessionConfig``).
In some cases this may be desirable functionality, in other cases one would like to isolate these overlays as such that they do not communicate with third parties.

How have we solved this in the past?
As you may know, part of the unique identification of a IPv8 overlay is its master peer definition.
Previously, one was required to create a subclass of the overlay under test in Gumby which had a different master peer definition.
Even though this is still possible, a system has been implemented in Gumby which allows you to easily isolate and/or replace these existing Tribler overlays or add your own.

Isolation
---------
To demonstrate the use of overlay isolation we will use the following subclass of ``TriblerExperimentScriptClient``:

.. code-block:: python

    class MyTriblerExperimentScriptClientSubclass(TriblerExperimentScriptClient):

        def create_overlay_loader(self):
            loader = super(MyTriblerExperimentScriptClientSubclass, self).create_community_loader()
            loader.isolate("HiddenTunnelCommunity")
            return loader

What we are doing here is overwriting the ``TriblerExperimentScriptClient.create_community_loader`` method and modifying the default ``IsolatedCommunityLoader`` it returns.
Specifically, we are asking the ``IsolatedCommunityLoader`` to isolate a community with the name ``"HiddenTunnelCommunity"``, which happens to be one of the communities loaded by default (if we don't modify the ``SessionConfig``).

You can also perform isolation with your own communities.
To do this, you will have to write your own launcher.
We will go over the basics of this in the following section.

My First CommunityLauncher
--------------------------
Now that you know how to isolate existing communities, let's go over adding your own communities to ``TriblerExperimentScriptClient``.
In this example we will create a custom ``CommunityLauncher``, in the next section we will discuss more advanced functionality which the ``CommunityLauncher`` offers.
Consider the following minimal example, which sets up a launcher for some community class ``MyFirstCommunity``:

.. code-block:: python

    class MyFirstCommunityLauncher(CommunityLauncher):

        def get_name(self):
            return "MyFirstCommunity"

        def get_community_class(self):
            return MyFirstCommunity

    class MyTriblerExperimentScriptClientSubclass(TriblerExperimentScriptClient):

        def create_community_loader(self):
            loader = super(MyTriblerExperimentScriptClientSubclass, self).create_community_loader()
            # Register our custom community
            loader.set_launcher(MyFirstCommunityLauncher())
            # Which we can isolate as well
            loader.isolate("MyFirstCommunity")
            return loader

As you can see, a minimal ``CommunityLauncher`` implementation requires a name and a community class to be defined.
A launcher is uniquely identified by its name.
**If you use ``set_launcher`` with an existing name, the current launcher will be overwritten.**
In some cases overwriting a default community entirely may be desired though.

CommunityLauncher Interface
---------------------------
The reference for the methods of the ``CommunityLauncher`` is as follows:

========================================== =========== ===========
Method                                     Type        Description
========================================== =========== ===========
``get_name()``                             *str*       The unique name of this launcher.
``not_before()``                           *list(str)* The names of launchers which should be loaded before this launcher is launched. Use in combination with ``prepare()`` to retrieve runtime information from other communities.
``should_launch(session)``                 *bool*      Checks the Session parameters to see if this community should be loaded.
``prepare(ipv8, session)``                 *None*      Prepare this launcher with information from the current ``Session``.
``finalize(ipv8, session, community)``     *None*      Called after the overlay has been loaded.
``get_overlay_class()``                    *Overlay*   The class of the overlay to be loaded by IPv8.
``get_my_peer(ipv8, session)``             *Member*    The IPv8 member to use for this community.
``should_load_now(session)``               *bool*      Load this overlay right now, should be ``True`` in most cases. The ``IsolatedCommunityWrapper`` uses this mechanism to provide a custom master member.
``get_args(session)``                      *tuple*     The arguments to supply to the ``__init__`` method of the loaded overlay class.
``get_kwargs(session)``                    *dict*      The named arguments to supply to the ``__init__`` method of the loaded overlay class.
========================================== =========== ===========
