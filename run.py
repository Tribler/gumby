#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from asyncio import ensure_future, get_event_loop, sleep
from signal import SIGKILL, SIGTERM, signal
from time import time

import psutil

from gumby.runner import ExperimentRunner

logging.basicConfig(level=getattr(logging, os.environ.get('GUMBY_LOG_LEVEL', 'INFO').upper()))
logging.getLogger("asyncio").setLevel(logging.WARNING)

_terminating = False


def _termTrap(self, *argv):
    if not _terminating:
        print("Captured TERM signal")
        _killGroup()
        exit(-15)


def _killGroup(signal=SIGTERM):
    global _terminating
    _terminating = True
    mypid = os.getpid()
    pids_found = 0
    for pid in psutil.pids():
        try:
            if os.getpgid(pid) == mypid and pid != mypid:
                os.kill(pid, signal)
                pids_found += 1
        except OSError:
            # The process could already be dead by the time we do the getpgid()
            pass
    return pids_found


async def run_experiment(conf_path):
    loop = get_event_loop()

    # Create a process group so we can clean up after ourselves when
    os.setpgrp()  # create new process group and become its leader
    # Catch SIGTERM to attempt to clean after ourselves
    signal(SIGTERM, _termTrap)

    logger = logging.getLogger()
    exp_runner = ExperimentRunner(conf_path)
    try:
        await exp_runner.run()
    except Exception as e:
        logger.error("Experiment execution failed, exiting with error.")
        logger.error(str(e))
        loop.exit_code = 1
        loop.stop()

    # Kill all the subprocesses before exiting
    logger.info("Killing leftover local sub processes...")
    pids_found = _killGroup()
    wait_start_time = time()
    while pids_found > 1 and (time() - wait_start_time) < 30:
        pids_found = _killGroup()
        if pids_found > 1:
            logger.info("Waiting for %d subprocess(es) to die...", pids_found)
        await sleep(5)

    if (time() - wait_start_time) >= 30:
        logger.info("Time out waiting, sending SIGKILL to remaining processes.")
        _killGroup(SIGKILL)

    logger.info("Experiment done")
    loop.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("confpath", help="The path to the experiment configuration file")
    args = parser.parse_args()

    if not os.path.exists(args.confpath):
        print("Error: The specified configuration file doesn't exist.")
        sys.exit(1)

    sys.path.append(os.path.dirname(__file__))
    ensure_future(run_experiment(args.confpath))
    loop = get_event_loop()
    loop.exit_code = 0
    loop.run_forever()
    loop.close()
    sys.exit(loop.exit_code)
