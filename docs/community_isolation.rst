***********************
Isolating IPv8 overlays
***********************

The purpose of this document is to show a means of isolating IPv8 overlays from outside interference in Gumby experiments.
This document assumes the reader has a basic understanding of running Gumby experiments, creating IPv8 overlays and running them.

As you may have noticed, some of the overlays loaded through Gumby are the actual overlays that are also re-used in production.
In some cases this may be desirable functionality, in other cases one would like to isolate these overlays as such that they do not communicate with third parties.

How have we solved this in the past?
As you may know, part of the unique identification of a IPv8 overlay is its community ID.
Previously, one was required to create a subclass of the overlay under test in Gumby which had a different overlay ID.
Even though this is still possible, a system has been implemented in Gumby which allows you to easily isolate and/or replace these existing overlays or add your own.

Isolation
---------
Isolating a particular community is as simple as adding the following line to a scenario file (before the IPv8 session starts):

.. code-block:: none

    @0:0 isolate_ipv8_overlay PingPongCommunity

In this case, Gumby will automatically search for the launcher associated with the ``PingPongCommunity`` and replace the existing launcher with an instance of ``IsolatedIPv8LauncherWrapper``.
All information in the existing launcher will be copied to the instance of ``IsolatedIPv8LauncherWrapper``.
The community ID will be randomized such that it becomes more difficult for the Gumby experiment to interfere with deployed communities.
