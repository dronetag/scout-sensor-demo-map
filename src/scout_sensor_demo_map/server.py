"""The web application: map page, WebSocket fan-out and the /state endpoint.

Data flows in through the two ingestion paths - HTTP POST (ingest_http.py)
and MQTT (ingest_mqtt.py) - onto the bus (bus.py), which broadcasts every
message to the connected WebSocket map clients and keeps the last minutes
in RecentState (state.py) for the instant /state bootstrap.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Awaitable, Callable, Optional, cast

import jinja2
from aiohttp import web

from . import bus
from .ingest_http import handle_heartbeat, handle_odid
from .ingest_mqtt import mqtt_handler
from .state import recent_state
from .storage import MessageStorage

logger = logging.getLogger("dt.receiver.map")


@web.middleware
async def forwarded_prefix_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
    if not prefix:
        return await handler(request)
    try:
        response = await handler(request)
    except web.HTTPException as exc:
        if exc.status in (301, 302, 303, 307, 308):
            location = exc.headers.get("Location", "")
            if location.startswith("/"):
                exc.headers["Location"] = prefix + location
        raise
    if response.status in (301, 302, 303, 307, 308):
        location = response.headers.get("Location", "")
        if location.startswith("/"):
            response.headers["Location"] = prefix + location
    return response


TEMPLATES_DIR: str = os.path.join(os.path.dirname(__file__), "templates")

_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(["html", "jinja"]),
)


def _make_url_func(request: web.Request) -> Callable[[str], str]:
    prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
    host = request.headers.get("X-Forwarded-Host", "") or request.headers.get("host", "")
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)

    def url(path: str = "") -> str:
        normalized = "/" + path.lstrip("/") if path else ""
        return f"{proto}://{host}{prefix}{normalized}"

    return url


# ---- Serve Map on /
async def handle_default(request: web.Request) -> web.Response:
    prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
    template = _jinja_env.get_template("index.jinja")
    content = template.render(prefix=prefix, url=_make_url_func(request))
    # Accept-Encoding advertises gzip support: SCOUT probes / with HEAD and
    # starts compressing its payloads when it sees this header
    return web.Response(
        text=content,
        content_type="text/html",
        headers={"Referrer-Policy": "origin", "Accept-Encoding": "gzip"},
    )


async def handle_state(request: web.Request) -> web.Response:
    """Current state - last-5-minutes sensors and detections, one per key."""
    return web.json_response(recent_state.snapshot())


# ---------- WebSocket Handler ----------
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws_type: str = request.match_info["type"]
    logger.debug("Request for WebSocket type: %s", ws_type)
    ws: web.WebSocketResponse = web.WebSocketResponse()
    await ws.prepare(request)

    if ws_type == "odid":
        bus.odid_clients.add(ws)
    elif ws_type == "heartbeat":
        bus.heartbeat_clients.add(ws)

    try:
        async for _ in ws:
            pass
    finally:
        bus.odid_clients.discard(ws)
        bus.heartbeat_clients.discard(ws)

    return ws


async def start_background(app: web.Application) -> None:
    storage_path = cast(Optional[Path], app.get("storage_path"))
    storage: Optional[MessageStorage] = None
    if storage_path is not None:
        storage = MessageStorage(storage_path)
        app["storage"] = storage

    app["odid_broadcast"] = asyncio.create_task(bus.broadcast(bus.odid_queue, bus.odid_clients))
    app["heartbeat_broadcast"] = asyncio.create_task(
        bus.broadcast(bus.heartbeat_queue, bus.heartbeat_clients)
    )
    if app.get("mqtt_addr"):
        app["mqtt_task"] = asyncio.create_task(
            mqtt_handler(app["mqtt_addr"], app["mqtt_port"], storage)
        )


async def cleanup_background(app: web.Application) -> None:
    for task_name in ["odid_broadcast", "heartbeat_broadcast", "mqtt_task"]:
        task = cast(asyncio.Task[None], app.get(task_name))
        if task:
            task.cancel()
    storage = cast(Optional[MessageStorage], app.get("storage"))
    if storage is not None:
        storage.close()


def create_app(
    mqtt_addr: str = "",
    mqtt_port: int = 1883,
    storage_path: Optional[Path] = None,
) -> web.Application:
    app: web.Application = web.Application(middlewares=[forwarded_prefix_middleware])
    app["mqtt_addr"] = mqtt_addr
    app["mqtt_port"] = mqtt_port
    app["storage_path"] = storage_path

    app.add_routes(
        [
            web.post("/odid", handle_odid),
            web.post("/heartbeat", handle_heartbeat),
            web.get("/ws/{type}", websocket_handler),
            web.get("/state", handle_state),
            web.get("/", handle_default),
        ]
    )

    app.on_startup.append(start_background)  # type: ignore[arg-type]
    app.on_cleanup.append(cleanup_background)  # type: ignore[arg-type]
    return app


def run(
    http_port: int = 9090,
    http_host: Optional[str] = None,
    mqtt_port: int = 1883,
    mqtt_addr: str = "",
    storage_path: Optional[Path] = None,
) -> None:
    app = create_app(mqtt_addr=mqtt_addr, mqtt_port=mqtt_port, storage_path=storage_path)
    web.run_app(app, host=http_host, port=http_port)
