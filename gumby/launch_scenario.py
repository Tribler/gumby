#!/usr/bin/env python3
import random
import sys
from asyncio import get_event_loop
from logging import debug
from os import environ, path
from sys import path as python_path

from gumby.log import setupLogging
from gumby.sync import ExperimentClientFactory
from gumby.util import run_task


def setup_environment_gumby():
    """
    Setup Gumby-related environment variables.
    """
    environ["PROJECT_DIR"] = environ.get("PROJECT_DIR", None) or path.abspath(path.join(path.dirname(__file__), ".."))
    environ["OUTPUT_DIR"] = environ.get("OUTPUT_DIR", None) or path.abspath(path.join(environ["PROJECT_DIR"], "output"))

    if "EXPERIMENT_DIR" not in environ:
        if "SCENARIO_FILE" in environ:
            # Assume that the experiment files are in the same directory as the scenario file
            environ["EXPERIMENT_DIR"] = path.abspath(path.dirname(environ["SCENARIO_FILE"]))
        else:
            environ["EXPERIMENT_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "experiments", "dummy"))

    if "SYNC_HOST" not in environ:
        if "SSH_CONNECTION" in environ:
            environ["SYNC_HOST"] = environ["SSH_CONNECTION"].split(" ")[0]
        else:
            environ["SYNC_HOST"] = "localhost"

    if environ["EXPERIMENT_DIR"] not in python_path:
        python_path.append(environ["EXPERIMENT_DIR"])


def setup_environment_other():
    """
    Setup environment variables related to various modules.
    """
    if "TRIBLER_DIR" not in environ:
        environ["TRIBLER_DIR"] = path.abspath(path.join(environ["PROJECT_DIR"], "tribler"))

    # Add the Tribler source directory to the Python path so we can import from them
    src_dir = path.join(environ["TRIBLER_DIR"], 'src')
    if src_dir not in python_path:
        python_path.append(src_dir)

    if "ANYDEX_DIR" in environ:
        python_path.append(environ["ANYDEX_DIR"])
    if "BAMI_DIR" in environ:
        python_path.append(environ["BAMI_DIR"])
    if "IPV8_DIR" in environ:
        python_path.append(environ["IPV8_DIR"])


def main():
    """
    This is the main entry point for synchronized Gumby experiments (the most common way to run an experiment
    using Gumby).
    The launch_scenario script will start the event loop and run an ExperimentClient on it.
    """
    if not environ["SYNC_PORT"]:
        print("Environment variable SYNC_PORT required.")
        sys.exit(1)

    setup_environment_gumby()
    setup_environment_other()

    setupLogging()

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
