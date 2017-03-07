The purpose of this document is to show a means of isolating Dispersy communities from outside interference in Gumby experiments.
This document assumes the reader has a basic understanding of running Gumby experiments, creating Dispersy communities and running them through the ``TriblerExperimentScriptClient`` class.

********************************************
Isolating and replacing Dispersy communities
********************************************
As you may have noticed, the communities loaded by the ``TriblerExperimentScriptClient`` are the live communities as loaded by Tribler (which you can toggle by setting the correct flags in the ``SessionConfig``).
In some cases this may be desirable functionality, in other cases one would like to isolate these communities as such that they do not communicate with third parties.

How have we solved this in the past?
As you may know, part of the unique identification of a Dispersy community is its master member definition.
Previously, one was required to create a subclass of the community under test in Gumby which had a different master member definition.
Even though this is still possible, a system has been implemented in Gumby which allows you to easily isolate and/or replace these existing Tribler communities or add your own.

Isolation
---------
To demonstrate the use of community isolation we will use the following subclass of ``TriblerExperimentScriptClient``:

.. code-block:: python

    class MyTriblerExperimentScriptClientSubclass(TriblerExperimentScriptClient):

        def create_community_loader(self):
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
``prepare(dispersy, session)``             *None*      Prepare this launcher with information from the current ``Session``.
``finalize(dispersy, session, community)`` *None*      Called after the community has been loaded. The community may be ``None`` if the ``load()`` setting evaluates to ``False`` or Dispersy failed to load the community.
``get_community_class()``                  *Community* The class of the community to be loaded by Dispersy.
``get_my_member(dispersy, session)``       *Member*    The Dispersy member to use for this community.
``should_load_now(session)``               *bool*      Load this community right now, should be ``True`` in most cases. The alternative is to call ``init_community()`` later. The ``IsolatedCommunityWrapper`` uses this mechanism to provide a custom master member.
``get_args(session)``                      *tuple*     The arguments to supply to the ``init_community()`` method of the loaded community class.
``get_kwargs(session)``                    *dict*      The named arguments to supply to the ``init_community()`` method of the loaded community class.
========================================== =========== ===========
