"""Unit tests for batched/compressed request body handling."""

import gzip
import json
import zlib

from scout_sensor_demo_map.payload import decompress_body, split_messages

MSG_A = {"sn": "A", "odid": {"BasicID": [{"UASID": "1"}]}}
MSG_B = {"sn": "B", "odid": {"BasicID": [{"UASID": "2"}]}}


def encode(*messages: dict, separator: str) -> str:
    return separator.join(json.dumps(m) for m in messages)


def parse_all(body: str) -> list[dict]:
    return [json.loads(m) for m in split_messages(body)]


def test_single_message_passes_through() -> None:
    assert parse_all(json.dumps(MSG_A)) == [MSG_A]


def test_lf_batch_is_split() -> None:
    assert parse_all(encode(MSG_A, MSG_B, separator="\n")) == [MSG_A, MSG_B]


def test_crlf_batch_is_split() -> None:
    assert parse_all(encode(MSG_A, MSG_B, separator="\r\n")) == [MSG_A, MSG_B]


def test_concatenated_batch_is_split() -> None:
    # SCOUT's "nothing" separator concatenates the JSON objects back to back
    assert parse_all(encode(MSG_A, MSG_B, separator="")) == [MSG_A, MSG_B]


def test_json_array_batch_is_split() -> None:
    assert parse_all(json.dumps([MSG_A, MSG_B])) == [MSG_A, MSG_B]


def test_trailing_newline_is_ignored() -> None:
    assert parse_all(encode(MSG_A, MSG_B, separator="\n") + "\n") == [MSG_A, MSG_B]


def test_invalid_json_passes_through_whole() -> None:
    assert split_messages("not json at all") == ["not json at all"]


def test_gzip_body_is_decompressed() -> None:
    raw = json.dumps(MSG_A).encode()
    assert decompress_body(gzip.compress(raw), "gzip") == raw


def test_gzip_recognized_without_header() -> None:
    # proxies may strip Content-Encoding - the gzip magic bytes are enough
    raw = json.dumps(MSG_A).encode()
    assert decompress_body(gzip.compress(raw), "") == raw


def test_deflate_body_is_decompressed() -> None:
    raw = json.dumps(MSG_A).encode()
    assert decompress_body(zlib.compress(raw), "deflate") == raw


def test_plain_body_is_untouched() -> None:
    assert decompress_body(b"plain", "") == b"plain"
