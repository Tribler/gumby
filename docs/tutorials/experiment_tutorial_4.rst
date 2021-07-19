Running an Experiment with IPv8 Overlays
========================================

In the previous tutorials, we have discussed how to run both experiments on a single computer and on the DAS5 cluster.
We now show how to combine Gumby experiments with IPv8 overlays and show how we can use Gumby to quickly test
decentralized overlays. We assume that the reader is familiar with IPv8 overlays.
Otherwise, we refer to the `IPv8 documentation <https://py-ipv8.readthedocs.io/en/latest/>`_ for more information.

In the following experiment, we spawn two instances and each instance joins a simple IPv8 community.
After five seconds, instance 1 sends a ``ping`` message to instance 2 and instance 2 responds with a ``pong`` message.
Our configuration file looks as follows:

.. literalinclude:: simple_ipv8.conf

All these configuration options have been discussed in previous tutorials.
Our scenario file looks as follows:

.. literalinclude:: simple_ipv8.scenario

There are several things going on here.
First, we call the ``isolate_ipv8_overlay`` method, which ensures that the overlay loaded in our experiments do not
communicate with peers external to our experiments.
After 1 second, we call the ``start_session`` method that starts the IPv8 service.
After 5 seconds, we introduce the peers to each other so peers know about each other and can send messages.
After 10 seconds, we call the ``send_ping`` message (defined in the ``PingPongModule`` class) which sends a ``ping``
message to all known peers.
We then stop the IPv8 service after 15 seconds and stop the entire experiment after 20 seconds.

Note that the scenario file imports the ``ping_pong_module.py`` file.
The content of this file is as follows:

.. literalinclude:: ping_pong_module.py

This file implements the following:

* We define two IPv8 payloads, namely ``PingPayload`` and ``PongPayload``.
* We define the ``PingPongCommunity`` class which contains some logic when receiving ping and pong messages.
* We implement a ``PingPongCommunityLauncher`` which is used by Gumby to correctly load the community on experiment startup.
* Finally, we implement the ``PingPongModule`` which contains a single experiment callback.

You can run the experiment with the following command:

.. code-block:: bash

   $ IPV8_DIR=<PATH TO IPV8> gumby/run.py gumby/docs/tutorials/simple_ipv8.conf

Note the ``IPV8_DIR`` environment variables which tells Gumby where to find the IPv8 source code.
You should change this to point to your IPv8 installation.
The experiment ends after around 20 seconds.
Inspecting the instance output should reveal log lines like:

.. code-block:: none

    2021-07-18 12:52:06,699:INFO:Sending ping to peer Peer<127.0.0.1:12002, s4WWx6gchewSqE27LpP+xBt8QsE=>
    2021-07-18 12:52:06,700:INFO:Received pong from peer Peer<127.0.0.1:12002, s4WWx6gchewSqE27LpP+xBt8QsE=>

This shows that the peers have successfully communicated with each other using IPv8 and Gumby.