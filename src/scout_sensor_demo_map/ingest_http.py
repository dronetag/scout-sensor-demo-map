"""HTTP ingestion - how SCOUT's "JSON+ODIDv2 over HTTP" forwarder feeds us.

SCOUT POSTs detections to /odid and status heartbeats to /heartbeat. A body
may be gzip-compressed and may batch several messages (see payload.py);
every individual message is published onto the bus.
"""

from typing import Optional, cast

from aiohttp import web

from . import bus
from .payload import decompress_body, split_messages
from .storage import MessageStorage


async def read_messages(request: web.Request) -> list[str]:
    raw = decompress_body(await request.read(), request.headers.get("Content-Encoding", "").lower())
    return split_messages(raw.decode())


async def handle_odid(request: web.Request) -> web.Response:
    storage = cast(Optional[MessageStorage], request.app.get("storage"))
    for data in await read_messages(request):
        await bus.publish_odid(data, storage, "http")
    return web.Response(text="ODID Received")


async def handle_heartbeat(request: web.Request) -> web.Response:
    storage = cast(Optional[MessageStorage], request.app.get("storage"))
    for data in await read_messages(request):
        await bus.publish_heartbeat(data, storage, "http")
    return web.Response(text="Heartbeat Received")
