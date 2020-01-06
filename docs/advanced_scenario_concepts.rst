***********************************
Advanced Scenario Language Concepts
***********************************

The document is meant to exemplify some of the more advanced features of the scenario language. Currently, these features refer to:

- Support for ``variables``
- Support for ``for`` loops

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

For Loops
---------

Often in scenario files, it might be useful to have the same operation executed multiple times by a peer, or have a single operation executed once on multiple peers. Without ``for`` loops both of these use cases are possible, but would demand quite a considerable amount of coding effort, usually requiring that one repeatedly copy-pastes the same line multiple times, making the code messy and difficult to alter when changes are required.

This is the reason why ``for`` loops have been added to scenario files, as they facilitate the writing and maintenance effort of such experiments.

The current implementation of ``for`` loops supports the execution of a single experiment callback. The callback can be passed the control variable as a parameter, and similarly, the control variable can be used as the peerspec of the callback. The general structure of the ``for`` loop is the following:

``@<timestamp> for <control_variable> in <left_bound> to <right_bound> call <callable> [<unnamed_parameters>]* [<named_parameters>]* [{<peerspec>}]``

The following is an explanation of the elements of the above command line:

- ``<timestamp>`` refers to the time into the experiment when the for loop should be executed, and implicitly its associated experiment callback
- ``<control_variable>`` refers to an alias assigned to the control variable, by which it can be referenced in the future
- ``<left_bound>`` refers to the initial value that the ``<control_variable>`` will take. This bound is inclusive, and need not be lower than the ``<right_bound>``
- ``<right_bound>`` refers to the final value of the ``<control_variable>``. This bound is inclusive, and need not be higher than the ``<left_bound>``.
- ``<callable>`` refers the experiment callback
- <unnamed_parameters> and <named_parameters> refer to the unnamed and named parameters that the callback takes. The programmer can use the ``<control_variable>`` as a parameter to the ``<callable>``.
- ``<peerspec>`` defines which peers should execute the ``for`` loop.

The Control Variable
~~~~~~~~~~~~~~~~~~~~

The control variable can be seen as a regular variable which is visible only during the for loop. It is referenced using the same construct as normal variables:

``$<control_variable>``

The control variable can be used as a parameter of the experiment callback. It should be mentioned however that **if there already is a declared variable with the same name as the control variable, the ``for`` loop will still work, but the variable will take precedence over the control variable when it is used as a parameter**.

The Iteration Bounds
~~~~~~~~~~~~~~~~~~~~

The ``<left_bound>`` and ``<right_bound>`` are specified as integers, and are both inclusive. There is no mandatory relationship between the two bounds: they can be equal, or one of them can be greater than the other.

Intuitively, if the bounds are equal, then the ``for`` loop will iterate once, and the control variable will be equal to the bounds. If, however, the ``<left_bound> < <right_bound>``, the control variable will move in increments of 1 towards the ``<right_bound>``, starting from the ``<left_bound>``. If the ``<left_bound> > <right_bound>``, the control variable will move in decrements of 1 towards the ``<right_bound>``, again starting from the ``<left_bound>``.

The Peerspec
~~~~~~~~~~~~

Peerspec is short for *peer specification*, and generally speaking, it allows one to specify which peers should execute a callback (or on the opposite, which peers shouldn't execute it). **The ``for`` loop still allows a peerspec to be used, however, its functionality is limited**. The peerspec can only contain one element, which can be one of the following:

- A literal which identifies a peer by its ID. In this case, the chosen peer will execute all the ``for`` loop's iterations
- The control variable. In this case, each iteration will select a peer to execute the operation, granted there is a peer with an ID that is the same as the control variable at that iteration

As such, it is currently not possible to specify multiple literals, specify which peers should *not* execute the iterations, or specify a mixture of the aforementioned entities, together with the control variable in the peerspec of a ``for`` loop.

Examples
~~~~~~~~

Let us take a closer look at some examples, which demonstrate how ``for`` loops can be used, and what are some of their limitations.

The following is a simple example which shows a ``for`` loop where the control variable moves in increments of 1 from 1 to 10. Each peer executing the scenario will run the associated experiment callback (``do_some_work``) 10 times, since no peerspec is used to select which peers should it:

``@0:25 for i in 1 to 10 call do_some_work``

The following ``for`` loop is exactly the same bar the fact that the control variable will move in decrements of 1 from 10 to 1:

``@0:25 for i in 10 to 1 call do_some_work``

It should be mentioned that if we want we can make one, or both of the bounds negative - the ``for`` should still work as expected -:

``@0:25 for i in -5 to 1 call do_some_work``

If we wish we can also make the bounds equal. In such a situation, there would only be one iteration, where the control variable takes on the value of the bounds:

``@0:25 for i in 1 to 1 call do_some_work``

It is possible to use the control variable as an unnamed parameter, named parameter, or both, to the ``for`` loop's associated experiment callback. If we imagine that our ``do_some_work`` function has the following new definition: ``def do_some_work(self, a, b=None, c=None)``, then we could, easily use the ``for`` loop's control variable as one or more parameters to this method. Let us take a look at a possible combination:

``@0:25 for i in 1 to 10 call do_some_work $i b=100 c=$i``

In this example, parameters ``a`` and ``c`` will be assigned the value of ``i``, and ``b`` will be assigned the constant ``100``.

For loops can also have an associated peerspec. Currently, it is only possible to use either a literal or the control variable within it. An example using a literal might look like this:

``@0:25 for i in 1 to 10 call do_some_work {1}``

Here, the peer with ID ``1`` will execute the ``do_some_work`` experiment callback 10 times, while any other peer will ignore the ``for`` loop. Using the control variable instead would look like this:

``@0:25 for i in 1 to 10 call do_some_work {$i}``

In this case, each of the ``for`` loop iterations will each be executed by a different peer as identified by the control variable in the given iterations.

Special Use Cases
~~~~~~~~~~~~~~~~~

A known special case is when the control variable's name is the same as a variable's. **The ``for`` loop should still work, but the code's behavior might be slightly different if the control variable is used as a parameter**. Let us look at an example describing this case:

.. code-block:: none

    @! set i foo

    ...

    @10:00 for i in 1 to 100 call my_function $i {$i}


It might not be immediately obvious what the behavior of this ``for`` loop will be, so let us take a closer look. Initially, a variable named ``i`` is declared, and is assigned the value ``foo``. Later on in the code, a ``for`` loop is defined, having a control variable with the same name as a regular variable: ``i``. The ``for`` loop will call ``my_function`` 100 times, and it will pass ``i`` as a parameter. **In this case, the variable will take precedence over the control variable, hence, the value passed to ``my_function`` will be ``foo``**. **The control variable will take precedence over the variable in the peerspec, thus, it will filter out peers as described above**.

Invalid Use Cases
~~~~~~~~~~~~~~~~~

The following examples will not work due invalid syntax:

- ``@0:25 for i in 1 to 10 call my_function {$}`` - the peerspec may not contain the ``$`` without a variable name
- ``@0:25 for i 1 to 10 call my_function`` - invalid ``for`` loop structure
- ``@0:25 for i in 1 10 call my_function`` - invalid ``for`` loop structure
- ``@0:25 for i in 1 to call my_function`` - invalid ``for`` loop structure
- ``@0:25 for i in to 10 call my_function`` - invalid ``for`` loop structure

The following will not work due to other issues:

- Usage of a (non-control) variable in the peerspec:

.. code-block:: none

    @! set j 1
    ...
    @10:00 for i in 1 to 100 call my_function $i {$j}

- Peer negation in the ``for`` loop's peerspec:

``@10:00 for i in 1 to 100 call my_function $i {!3}``

- Multiple peer IDs in the ``for`` loop's peerspec:

``@10:00 for i in 1 to 100 call my_function $i {1,2,3,4}``
