#!/usr/bin/env python3
import os
from asyncio import ensure_future, get_event_loop, sleep
from pathlib import Path

from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.session import Session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


class IdleTribleRunner:

    def __init__(self):
        self.session = None

    async def run(self):
        state_dir = Path(os.path.abspath(os.path.join(BASE_DIR, "output", "tribler-state")))
        config = TriblerConfig(state_dir=state_dir)
        config.api.http_enabled = False
        config.ipv8.port = 21000
        config.libtorrent.port = 21005

        self.session = Session(config)
        try:
            await self.session.start()
        except Exception as e:
            print(str(e))
            get_event_loop().stop()
        else:
            print("Tribler started")

        if "TRIBLER_EXECUTION_TIME" in os.environ:
            run_time = int(os.environ["TRIBLER_EXECUTION_TIME"])
        else:
            run_time = 60 * 10  # Run for 10 minutes by default

        await sleep(run_time)

        print("Stopping Tribler idle run")
        await self.session.shutdown()
        get_event_loop().stop()


if __name__ == "__main__":
    runner = IdleTribleRunner()
    ensure_future(runner.run())
    get_event_loop().run_forever()
    get_event_loop().close()
