#!/usr/bin/env python3
import random
from asyncio import ensure_future, get_event_loop
from logging import debug, warning
from os import environ, path
from sys import argv, path as python_path

from gumby.log import setupLogging
from gumby.sync import ExperimentClientFactory, ExperimentServiceFactory
from gumby.util import run_task


# @CONF_OPTION SCENARIO_FILE: The scenario to run for this experiment (default: None)

def main():
    """
    This is the main entry point for gumby experiments that run a scenario file.
    To use it you must either:
     - Supply a scenario file to run on the commandline (eg: launch_scenario.py some.scenario), or
     - Set the scenario file to run in the SCENARIO_FILE environment variable.

    The launch_scenario script will start the event loop and run an ExperimentClient on it.
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
        environ["OUTPUT_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "output"))
    if "TRIBLER_DIR" not in environ:
        environ["TRIBLER_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "tribler"))
    if "IPV8_DIR" not in environ:
        environ["IPV8_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "tribler", "src", "pyipv8"))
    if "ANYDEX_DIR" in environ:
        python_path.append(environ["ANYDEX_DIR"])
    if "BAMI_DIR" in environ:
        python_path.append(environ["BAMI_DIR"])
    if "SYNC_HOST" not in environ:
        # If we deploy using an SSH connection, use the IP of the host
        if "SSH_CONNECTION" in environ:
            environ["SYNC_HOST"] = environ["SSH_CONNECTION"].split(" ")[0]
        else:
            environ["SYNC_HOST"] = "localhost"
    if "SYNC_PORT" not in environ:
        environ['SYNC_PORT'] = "0"
    if "SCENARIO_FILE" not in environ:
        environ["SCENARIO_FILE"] = path.abspath(path.join(
            environ["EXPERIMENT_DIR"], "%s.scenario" % path.basename(path.normpath(environ["EXPERIMENT_DIR"]))))

    for subdir_name in ('tribler-common', 'tribler-core'):
        subdir_path = path.join(environ["TRIBLER_DIR"], 'src', subdir_name)
        if subdir_path not in python_path:
            python_path.append(subdir_path)
    if environ["EXPERIMENT_DIR"] not in python_path:
        python_path.append(environ["EXPERIMENT_DIR"])
    if environ["IPV8_DIR"] not in python_path:
        python_path.append(environ["IPV8_DIR"])

    setupLogging()
    if not path.exists(environ["SCENARIO_FILE"]):
        warning("Unable to find scenario file: %s", environ["SCENARIO_FILE"])

    loop = get_event_loop()
    loop.exit_code = 0

    debug("Connecting to: %s:%s", environ['SYNC_HOST'], int(environ['SYNC_PORT']))
    run_task(loop.create_connection, ExperimentClientFactory(), environ['SYNC_HOST'],
             int(environ['SYNC_PORT']), delay=random.randint(1, 5))
    loop.run_forever()
    loop.close()
    exit(loop.exit_code)


if __name__ == '__main__':
    main()
