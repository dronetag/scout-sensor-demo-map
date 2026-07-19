"""MQTT ingestion - the alternative to HTTP for brokered deployments.

Subscribes to the `odid` and `heartbeat` topics of the configured broker
and publishes every individual message onto the bus. Payloads may use the
same compression and batching as the HTTP path (see payload.py).
"""

from typing import Optional

import aiomqtt

from . import bus
from .payload import decompress_body, split_messages
from .storage import MessageStorage


async def mqtt_handler(
    mqtt_addr: str, mqtt_port: int, storage: Optional[MessageStorage] = None
) -> None:
    async with aiomqtt.Client(hostname=mqtt_addr, port=mqtt_port) as client:
        await client.subscribe("odid")
        await client.subscribe("heartbeat")

        async for message in client.messages:
            raw = message.payload if isinstance(message.payload, bytes) else str(message.payload).encode()
            topic: str = message.topic.value
            if topic == "odid":
                for payload in split_messages(decompress_body(raw, "").decode()):
                    await bus.publish_odid(payload, storage, "mqtt")
            elif topic == "heartbeat":
                for payload in split_messages(decompress_body(raw, "").decode()):
                    await bus.publish_heartbeat(payload, storage, "mqtt")
