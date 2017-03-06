from logging import debug, error
from twisted.internet import reactor
from os import environ, path
from random import random
from sys import path as python_path, argv

from gumby.instrumentation import init_instrumentation
from gumby.log import setupLogging
from gumby.sync import ExperimentClientFactory, ExperimentServiceFactory


def main(self_service=False):
    if len(argv) > 2:
        print "Launch invoke error, to many command line arguments. Specify 1 scenario file to run."
        return

    if len(argv) == 2:
        p = path.abspath(argv[1])
        if path.exists(p):
            print "Launch error, command line argument %s does not exist" % p
        elif "SCENARIO_FILE" in environ:
            print "Launch invoke error, can't take both a command line scenario file and ean nvironment scenario file."
            return
        else:
            environ["SCENARIO_FILE"] = p

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

    python_path.append(environ["TRIBLER_DIR"])

    init_instrumentation()
    setupLogging()
    if not path.exists(environ["SCENARIO_FILE"]):
        error("Unable to find scenario file: %s", environ["SCENARIO_FILE"])

    reactor.exitCode = 0

    # if self service is requested, start an experiment server to run our scenario. Used to debug the client in an IDE
    if self_service or "GUMBY_SELF_SERVICE" in environ:
        environ["SYNC_HOST"] = "localhost"
        if environ["SYNC_PORT"] == "0":
            environ["SYNC_PORT"] = "57756"       # corresponds to the keyboard rows for the word gumby
        debug("Starting experiment server on: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))

        def exp_started(_):
            debug("Experiment started, closing server")

        fact = ExperimentServiceFactory(1, 3)
        fact.onExperimentStarted = exp_started
        reactor.listenTCP(int(environ['SYNC_PORT']), fact)

    debug("Connecting to: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))
    reactor.callLater(1 + random() * 10, reactor.connectTCP,
                      environ['SYNC_HOST'], int(environ['SYNC_PORT']), ExperimentClientFactory({}))
    reactor.run()
    exit(reactor.exitCode)

if __name__ == '__main__':
    main()