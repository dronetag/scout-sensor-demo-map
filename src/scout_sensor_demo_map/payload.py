"""SCOUT wire-format handling: transport compression and message batching.

SCOUT's JSON+ODIDv2 forwarder may gzip payloads and may batch several JSON
messages into one body - joined with "", "\\n" or "\\r\\n", or as a JSON
array. These helpers turn any such body back into individual JSON messages
and are shared by every ingestion path.
"""

import gzip
import json
import logging
import zlib

logger = logging.getLogger("dt.receiver.map")


def decompress_body(raw: bytes, content_encoding: str) -> bytes:
    """Undo the transport compression of a request body.

    Gzip is recognized by its magic bytes so it works whether or not the
    Content-Encoding header survived proxies; deflate is header-driven.
    """
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    if content_encoding == "deflate":
        return zlib.decompress(raw)
    return raw


def split_messages(body: str) -> list[str]:
    """Split a possibly batched request body into individual JSON messages.

    SCOUT's batching joins messages with "", "\\n" or "\\r\\n", or wraps them
    in a JSON array - a raw_decode loop handles all of those (and a plain
    single message). A body that is not valid JSON is passed through whole.
    """
    decoder = json.JSONDecoder()
    messages: list[str] = []
    index, end = 0, len(body)
    try:
        while index < end:
            while index < end and body[index] in " \t\r\n":
                index += 1
            if index >= end:
                break
            value, index = decoder.raw_decode(body, index)
            if isinstance(value, list):
                messages.extend(json.dumps(item, separators=(",", ":")) for item in value)
            else:
                messages.append(json.dumps(value, separators=(",", ":")))
    except json.JSONDecodeError:
        logger.warning("Received a body that is not (batched) JSON; passing through unsplit")
        return [body]
    return messages
