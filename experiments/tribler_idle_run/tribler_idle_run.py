#!/usr/bin/env python3
import os
import signal
from asyncio import ensure_future, get_event_loop, sleep
from pathlib import Path

from tribler_core.components.base import Session
from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.start_core import components_gen

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


async def idle_tribler_run():
    state_dir = Path(os.path.abspath(os.path.join(BASE_DIR, "output", "tribler-state")))
    config = TriblerConfig(state_dir=state_dir)
    config.api.http_enabled = False
    config.ipv8.port = 21000
    config.libtorrent.port = 21005

    components = components_gen(config)
    session = Session(config, components)
    signal.signal(signal.SIGTERM, lambda signum, stack: session.shutdown_event.set)
    session.set_as_default()

    try:
        await session.start_components()
    except Exception as e:
        print(str(e))
        return

    print("Tribler started")

    if "TRIBLER_EXECUTION_TIME" in os.environ:
        run_time = int(os.environ["TRIBLER_EXECUTION_TIME"])
    else:
        run_time = 60 * 10  # Run for 10 minutes by default

    await sleep(run_time)

    print("Stopping Tribler idle run")
    session.shutdown_event.set()

    # Indicates we are shutting down core. With this environment variable set
    # to 'TRUE', RESTManager will no longer accept any new requests.
    os.environ['TRIBLER_SHUTTING_DOWN'] = "TRUE"

    await session.shutdown()

    get_event_loop().stop()


if __name__ == "__main__":
    ensure_future(idle_tribler_run())
    get_event_loop().run_forever()
    get_event_loop().close()
