import asyncio
import logging
import os
from typing import Dict, Set, Union, cast

import aiomqtt
from aiohttp import web

logger = logging.getLogger("dt.receiver.map")

STATIC_DIR: str = os.path.join(os.path.dirname(__file__), "static")

# Queues for incoming ODID and heartbeat messages
odid_queue: asyncio.Queue[str] = asyncio.Queue()
heartbeat_queue: asyncio.Queue[str] = asyncio.Queue()

# Sets of active WebSocket clients
odid_clients: Set[web.WebSocketResponse] = set()
heartbeat_clients: Set[web.WebSocketResponse] = set()


# ---- Serve Map on /
async def handle_default(request: web.Request) -> web.FileResponse:
    return web.FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ---------- WebSocket Broadcaster ----------
async def broadcast(queue: asyncio.Queue[str], clients: Set[web.WebSocketResponse]) -> None:
    while True:
        msg = await queue.get()
        if clients:
            await asyncio.gather(*(client.send_str(msg) for client in clients if not client.closed))


# ---------- WebSocket Handler ----------
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws_type: str = request.match_info["type"]
    logger.debug("Request for WebSocket type: %s", ws_type)
    ws: web.WebSocketResponse = web.WebSocketResponse()
    await ws.prepare(request)

    if ws_type == "odid":
        odid_clients.add(ws)
    elif ws_type == "heartbeat":
        heartbeat_clients.add(ws)

    try:
        async for _ in ws:
            pass
    finally:
        odid_clients.discard(ws)
        heartbeat_clients.discard(ws)

    return ws


# ---------- HTTP Endpoints ----------
async def handle_odid(request: web.Request) -> web.Response:
    data: str = await request.text()
    await odid_queue.put(data)
    logger.debug("HTTP ODID data received: %s", data)
    return web.Response(text="ODID Received")


async def handle_heartbeat(request: web.Request) -> web.Response:
    data: str = await request.text()
    logger.debug("HTTP HEARTBEAT data received: %s", data)
    await heartbeat_queue.put(data)
    return web.Response(text="Heartbeat Received")


# ---------- MQTT Subscriber with aiomqtt ----------
async def mqtt_handler(mqtt_addr: str, mqtt_port: int) -> None:
    client_kwargs: Dict[str, Union[str, int]] = {
        "hostname": mqtt_addr,
        "port": mqtt_port,
    }

    async with aiomqtt.Client(**client_kwargs) as client:
        await client.subscribe("odid")
        await client.subscribe("heartbeat")

        async for message in client.messages:
            payload: str = message.payload.decode()
            topic: str = message.topic.value
            if topic == "odid":
                logger.debug("MQTT ODID data received: %s", payload)
                await odid_queue.put(payload)
            elif topic == "heartbeat":
                logger.debug("MQTT HEARTBEAT data received: %s", payload)
                await heartbeat_queue.put(payload)


async def start_background(app: web.Application) -> None:
    app["odid_broadcast"] = asyncio.create_task(broadcast(odid_queue, odid_clients))
    app["heartbeat_broadcast"] = asyncio.create_task(broadcast(heartbeat_queue, heartbeat_clients))
    app["mqtt_task"] = asyncio.create_task(mqtt_handler(app["mqtt_addr"], app["mqtt_port"]))


async def cleanup_background(app: web.Application) -> None:
    for task_name in ["odid_broadcast", "heartbeat_broadcast", "mqtt_task"]:
        task = cast(asyncio.Task[None], app.get(task_name))
        if task:
            task.cancel()


def run(http_port: int = 9090, mqtt_port: int = 1883, mqtt_addr: str = "") -> None:
    app: web.Application = web.Application()
    app["mqtt_addr"] = mqtt_addr
    app["mqtt_port"] = mqtt_port

    # Serve static files
    app.router.add_static("/static", path=STATIC_DIR, name="static")

    # Add routes
    app.add_routes(
        [
            web.post("/odid", handle_odid),
            web.post("/heartbeat", handle_heartbeat),
            web.get("/ws/{type}", websocket_handler),
            web.get("/", handle_default),
        ]
    )

    app.on_startup.append(start_background)
    app.on_cleanup.append(cleanup_background)
    web.run_app(app, port=http_port)
