#!/usr/bin/env python3
import asyncio
import os
import signal
import sys
from pathlib import Path

from tribler_core.components.base import Session
from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.start_core import components_gen

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DEFAULT_EXECUTION_TIME = 60 * 10  # Run for 10 minutes by default


async def run_session(config, session):
    signal.signal(signal.SIGTERM, lambda signum, stack: session.shutdown_event.set)
    try:
        async with session.start() as session:
            if config.error:
                session.logger.error(f'Config error: {config.error}')
                sys.exit(-1)

            session.logger.info("Tribler started")
            await session.shutdown_event.wait()
            session.logger.info("Stopping Tribler idle run")

    except Exception as e:  # pylint: disable=broad-except
        session.logger.exception(e)
        raise


async def end_session(session, execution_time):
    await asyncio.sleep(execution_time)
    session.shutdown_event.set()


def idle_tribler_run():
    state_dir = Path(os.path.abspath(os.path.join(BASE_DIR, "output", "tribler-state")))
    config = TriblerConfig(state_dir=state_dir)
    config.api.http_enabled = False
    config.ipv8.port = 21000
    config.libtorrent.port = 21005

    components = list(components_gen(config))
    session = Session(config, components)

    execution_time = int(os.environ.get("TRIBLER_EXECUTION_TIME", DEFAULT_EXECUTION_TIME))

    loop = asyncio.get_event_loop()
    loop.create_task(end_session(session, execution_time))
    loop.run_until_complete(run_session(config, session))


if __name__ == "__main__":
    idle_tribler_run()
