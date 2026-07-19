import asyncio
import socket
import threading
from typing import Generator

import pytest
from aiohttp import web

from scout_sensor_demo_map import server


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    port = _free_port()
    loop = asyncio.new_event_loop()
    ready = threading.Event()

    async def _serve() -> None:
        # no MQTT broker in tests - create_app skips the MQTT task without an address
        app = server.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()
        ready.set()
        await asyncio.Future()  # run until loop is stopped from outside

    def _thread() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_serve())
        except Exception:
            pass

    t = threading.Thread(target=_thread, daemon=True)
    t.start()
    assert ready.wait(timeout=10), "Test server did not start in time"
    yield f"http://localhost:{port}"
    loop.call_soon_threadsafe(loop.stop)
