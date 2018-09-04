#!/usr/bin/env python3

from logging import debug, warning
from twisted.internet import reactor
from os import environ, path
from sys import path as python_path, argv

from gumby.instrumentation import init_instrumentation
from gumby.log import setupLogging
from gumby.sync import ExperimentClientFactory, ExperimentServiceFactory


# @CONF_OPTION SCENARIO_FILE: The scenario to run for this experiment (default: None)

def main(self_service=False):
    """
    This is the main entry point for gumby experiments that run a scenario file.
    To use it you must either:
     - Supply a scenario file to run on the commandline (eg: launch_scenario.py some.scenario), or
     - Set the scenario file to run in the SCENARIO_FILE environment variable.

    The launch_scenario script will start the twisted reactor and run an ExperimentClient on it.

    For debugging a scenario in an IDE, launch_scenario offers the self_service feature. it is activated if the
    environment variable SELF_SERVICE exists, or if the main() method is invoked with self_service=True. The self-
    service feature starts an the experiment server on the reactor and uses it to start the experiment in the usual way.
    The self-service feature overrides the sync_host environment variable to 'localhost' and the sync_port variable if
    it was not set or if it was set to 0.
    """

    if len(argv) > 2:
        print("Launch invoke error, too many command line arguments. Specify 1 scenario file to run.")
        exit(3)

    if len(argv) == 2:
        scenario_argument = path.abspath(argv[1])
        if "SCENARIO_FILE" in environ:
            print("Launch invoke error, can't take both a command line scenario file and an environment scenario file.")
            exit(3)
        else:
            environ["SCENARIO_FILE"] = scenario_argument

    # setup the environment
    if "PROJECT_DIR" not in environ:
        environ["PROJECT_DIR"] = path.abspath(path.join(path.dirname(__file__), ".."))
    if "EXPERIMENT_DIR" not in environ:
        if "SCENARIO_FILE" in environ:
            environ["EXPERIMENT_DIR"] = path.abspath(path.dirname(environ["SCENARIO_FILE"]))
        else:
            environ["EXPERIMENT_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "experiments", "dummy"))
    if "OUTPUT_DIR" not in environ:
        environ["OUTPUT_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "..", "output"))
    if "TRIBLER_DIR" not in environ:
        environ["TRIBLER_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "..", "tribler"))
    if "SYNC_HOST" not in environ:
        environ["SYNC_HOST"] = "localhost"
    if "SYNC_PORT" not in environ:
        environ['SYNC_PORT'] = "0"
    if "SCENARIO_FILE" not in environ:
        environ["SCENARIO_FILE"] = path.abspath(path.join(
            environ["EXPERIMENT_DIR"], "%s.scenario" % path.basename(path.normpath(environ["EXPERIMENT_DIR"]))))

    if environ["TRIBLER_DIR"] not in python_path:
        python_path.append(environ["TRIBLER_DIR"])
    if environ["EXPERIMENT_DIR"] not in python_path:
        python_path.append(environ["EXPERIMENT_DIR"])

    init_instrumentation()
    setupLogging()
    if not path.exists(environ["SCENARIO_FILE"]):
        warning("Unable to find scenario file: %s", environ["SCENARIO_FILE"])

    reactor.exitCode = 0

    # if self service is requested, start an experiment server to run our scenario. Used to debug the client in an IDE
    if self_service or "SELF_SERVICE" in environ:
        environ["SYNC_HOST"] = "localhost"
        if environ["SYNC_PORT"] == "0":
            environ["SYNC_PORT"] = "57756"       # corresponds to the keyboard rows for the word gumby
        debug("Starting experiment server on: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))

        def exp_started(_):
            debug("Experiment started, closing server")

        # create experiment service with 1 expected subscriber, and start in 0 seconds
        fact = ExperimentServiceFactory(1, 0)
        # need to monkey patch this one or it will kill the reactor.
        fact.onExperimentStarted = exp_started
        reactor.listenTCP(int(environ['SYNC_PORT']), fact)

    debug("Connecting to: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))
    reactor.callLater(1, reactor.connectTCP,
                      environ['SYNC_HOST'], int(environ['SYNC_PORT']), ExperimentClientFactory())
    reactor.run()
    exit(reactor.exitCode)

if __name__ == '__main__':
    main()
