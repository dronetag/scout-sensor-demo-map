"""The in-process message bus between ingestion and the WebSocket clients.

Both ingestion paths (see ingest_http.py and ingest_mqtt.py) publish every
individual message here; publishing persists it (optional), remembers it in
RecentState for the /state endpoint and queues it for the `broadcast` tasks
that fan it out to the connected WebSocket clients.
"""

import asyncio
import logging
from typing import Optional, Set

from aiohttp import web

from .state import recent_state
from .storage import MessageStorage

logger = logging.getLogger("dt.receiver.map")

# Queues for incoming ODID and heartbeat messages
odid_queue: asyncio.Queue[str] = asyncio.Queue()
heartbeat_queue: asyncio.Queue[str] = asyncio.Queue()

# Sets of active WebSocket clients
odid_clients: Set[web.WebSocketResponse] = set()
heartbeat_clients: Set[web.WebSocketResponse] = set()


async def publish_odid(message: str, storage: Optional[MessageStorage], source: str) -> None:
    if storage is not None:
        storage.write_odid(message, source)
    recent_state.add_odid(message)
    await odid_queue.put(message)
    logger.debug("%s ODID data received: %s", source.upper(), message)


async def publish_heartbeat(message: str, storage: Optional[MessageStorage], source: str) -> None:
    if storage is not None:
        storage.write_heartbeat(message, source)
    recent_state.add_heartbeat(message)
    await heartbeat_queue.put(message)
    logger.debug("%s HEARTBEAT data received: %s", source.upper(), message)


async def broadcast(queue: asyncio.Queue[str], clients: Set[web.WebSocketResponse]) -> None:
    while True:
        msg = await queue.get()
        if clients:
            # return_exceptions: one client dying mid-send must not kill the
            # broadcast task (and with it live updates for everyone, forever)
            results = await asyncio.gather(
                *(client.send_str(msg) for client in list(clients) if not client.closed),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.debug("Dropped a broadcast to a dead client: %s", result)
