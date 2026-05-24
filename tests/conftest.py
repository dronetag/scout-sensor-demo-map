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
        app = web.Application(middlewares=[server.forwarded_prefix_middleware])
        app.add_routes(
            [
                web.post("/odid", server.handle_odid),
                web.post("/heartbeat", server.handle_heartbeat),
                web.get("/ws/{type}", server.websocket_handler),
                web.get("/", server.handle_default),
            ]
        )
        asyncio.create_task(server.broadcast(server.odid_queue, server.odid_clients))
        asyncio.create_task(
            server.broadcast(server.heartbeat_queue, server.heartbeat_clients)
        )
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
