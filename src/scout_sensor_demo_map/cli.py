import argparse
import asyncio
import os
import subprocess
from typing import Dict, Set, Union

import aiomqtt
from aiohttp import web

# Queues for incoming ODID and heartbeat messages
odid_queue: asyncio.Queue[str] = asyncio.Queue()
heartbeat_queue: asyncio.Queue[str] = asyncio.Queue()

# Sets of active WebSocket clients
odid_clients: Set[web.WebSocketResponse] = set()
heartbeat_clients: Set[web.WebSocketResponse] = set()


# ---------- WebSocket Broadcaster ----------
async def broadcast(queue: asyncio.Queue[str], clients: Set[web.WebSocketResponse]) -> None:
    while True:
        msg = await queue.get()
        if clients:
            await asyncio.gather(*(client.send_str(msg) for client in clients if not client.closed))


# ---------- WebSocket Handler ----------
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws_type: str = request.match_info["type"]
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
    return web.Response(text="ODID Received")


async def handle_heartbeat(request: web.Request) -> web.Response:
    data: str = await request.text()
    await heartbeat_queue.put(data)
    return web.Response(text="Heartbeat Received")


# ---------- MQTT Subscriber with aiomqtt ----------
async def mqtt_handler(mqtt_port: int) -> None:
    client_kwargs: Dict[str, Union[str, int]] = {
        "hostname": "localhost",
        "port": mqtt_port,
    }

    async with aiomqtt.Client(**client_kwargs) as client:
        await client.subscribe("odid")
        await client.subscribe("heartbeat")

        async for message in client.messages:
            payload: str = message.payload.decode()
            topic: str = message.topic.value
            if topic == "odid":
                await odid_queue.put(payload)
            elif topic == "heartbeat":
                await heartbeat_queue.put(payload)


# ---------- Mosquitto Process Starter ----------
def start_mosquitto(mosquitto_port: int) -> subprocess.Popen:
    mosquitto_cmd = ["mosquitto", "-p", str(mosquitto_port)]
    return subprocess.Popen(mosquitto_cmd)


# ---------- App Lifecycle ----------
async def start_background(app: web.Application) -> None:
    app["odid_broadcast"] = asyncio.create_task(broadcast(odid_queue, odid_clients))
    app["heartbeat_broadcast"] = asyncio.create_task(broadcast(heartbeat_queue, heartbeat_clients))
    app["mqtt_task"] = asyncio.create_task(mqtt_handler(app["mqtt_port"]))


async def cleanup_background(app: web.Application) -> None:
    for task_name in ["odid_broadcast", "heartbeat_broadcast", "mqtt_task"]:
        task = app.get(task_name)
        if task:
            task.cancel()


# ---------- aiohttp App ----------
app: web.Application = web.Application()

# Serve static files
static_path: str = os.path.join(os.path.dirname(__file__), "static")
app.router.add_static("/static", path=static_path, name="static")


# Serve default page
async def handle_default(request: web.Request) -> web.FileResponse:
    return web.FileResponse(os.path.join(static_path, "index.html"))


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


# ---------- Main ----------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the server with WebSocket and MQTT support."
    )
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP server port.")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port.")
    args = parser.parse_args()

    # Store MQTT config in app state
    app["mqtt_port"] = args.mqtt_port

    mosquitto_proc = start_mosquitto(args.mqtt_port)

    try:
        web.run_app(app, port=args.http_port)
    finally:
        mosquitto_proc.terminate()


if __name__ == "__main__":
    main()
