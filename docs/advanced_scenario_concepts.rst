***********************************
Advanced Scenario Language Concepts
***********************************

The document is meant to exemplify some of the more advanced features of the scenario language. Currently, these features refer to:

- Support for ``variables``

They will be exemplified and presented in further detail in the sections to follow:

Variables
---------

Variables have been introduced in the scenario language mainly for those cases when a value is repeatedly used during an experiment. Without variables this would force a programmer to frequently rewrite or copy-paste the literal, which may introduce human-made errors, and is at the very least cumbersome and tiring. Variables can help with this issue, by associating a value to a name / alias.

Variables are by default **strings**, and it is the responsibility of the programmer to ensure that they convert the string value to whatever type they require in the function code. This, however, does not differ to how normal literal parameters need to be processed within a function, as they are **strings** by default as well.

The syntax for declaring a variable is the following:

``@! set <variable_name> <variable_value>``

**The scope of the variable begins immediately and persists until the end of the scenario file**. The meaning of each component is explained in what follows:

- ``@!`` is a special timestamp which informs the parser that the command must be executed immediately, as opposed to using asyncio to schedule it in the future, after the scenario has been parsed and the experiment has begun.
- ``set`` is a special experiment callback, which is used to declare variables
- ``<variable_name>`` is the name of the variable
- ``<variable_value>`` is the value assigned to the variable

One can redefine a variable multiple times, and **the scope of the new value begins immediately, while the scope of the previous value will end immediately as well**.

In order to use the variable itself, one simply prepends the name of the variable with ``$`` and uses it as a parameter, as in the following example:

``@0:10 emit_value $myVal``

In the previous example, we assume that ``myVal`` is a variable which has been previously set using something like ``!@ set myVal <variable_value>``.

To better exemplify the usefulness of a variable within a scenario file let us look at a more extensive use case:

.. code-block:: none

    &module gumby.modules.tribler_module.TriblerModule
    &module experiments.dht.dht_module.DHTModule
    @0:0 isolate_ipv8_overlay DHTDiscoveryCommunity
    @0:1 start_session
    @0:1 annotate start-experiment
    @0:5 introduce_peers
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {2}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {3}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {4}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {5}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {6}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {7}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {8}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {9}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {10}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {11}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {12}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {13}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {14}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {15}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {16}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {17}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {18}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {19}
    @0:10 start_queries 10d00d55231921911991e2f7fd538ec989a2df00 {20}
    @0:10 store 10d00d55231921911991e2f7fd538ec989a2df00 value_to_store {1}
    @0:50 annotate end-experiment
    @0:50 stop_session
    @0:55 stop

In this example, we will have 20 active peers, 19 of which are querying each other for a particular datum, identified by a key (``d00d55231921911991e2f7fd538ec989a2df00`` in this case), while the 20th is publishing the aforementioned datum. One can easily see that copy-pasting the key throughout the scenario is a cumbersome task, and may introduce errors. To this extent, one can simplify the scenario by introducing variables:

.. code-block:: none

    &module gumby.modules.tribler_module.TriblerModule
    &module experiments.dht.dht_module.DHTModule
    @0:0 isolate_ipv8_overlay DHTDiscoveryCommunity
    @0:1 start_session
    @0:1 annotate start-experiment
    @0:5 introduce_peers
    @! set key 10d00d55231921911991e2f7fd538ec989a2df00
    @0:10 start_queries $key {2}
    @0:10 start_queries $key {3}
    @0:10 start_queries $key {4}
    @0:10 start_queries $key {5}
    @0:10 start_queries $key {6}
    @0:10 start_queries $key {7}
    @0:10 start_queries $key {8}
    @0:10 start_queries $key {9}
    @0:10 start_queries $key {10}
    @0:10 start_queries $key {11}
    @0:10 start_queries $key {12}
    @0:10 start_queries $key {13}
    @0:10 start_queries $key {14}
    @0:10 start_queries $key {15}
    @0:10 start_queries $key {16}
    @0:10 start_queries $key {17}
    @0:10 start_queries $key {18}
    @0:10 start_queries $key {19}
    @0:10 start_queries $key {20}
    @0:10 store 10$key value_to_store {1}
    @0:50 annotate end-experiment
    @0:50 stop_session
    @0:55 stop

The variable introduces a cleaner scenario. Moreover, if further changes are required to the key, one can simply change the value once, when the ``key`` is set. Previously, if the key needed to be changed, one would have to manually go through each of its occurrences and make the required modification.

