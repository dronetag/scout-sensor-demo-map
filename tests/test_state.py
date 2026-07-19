"""Tests for the last-5-minutes state (RecentState) and the /state endpoint."""

import json
import urllib.request

import pytest

from scout_sensor_demo_map.state import RecentState


def odid(uasid: str, lat: float) -> str:
    return json.dumps({"sn": "S", "odid": {"BasicID": [{"UASID": uasid}],
                                           "Location": {"Latitude": lat, "Longitude": 14.0}}})


def heartbeat(sn: str, satellites: int = 7) -> str:
    return json.dumps({"sn": sn, "gnss_satellites": satellites})


def test_detections_deduplicate_by_uasid() -> None:
    state = RecentState()
    state.add_odid(odid("DRONE1", 50.0))
    state.add_odid(odid("DRONE1", 51.0))
    state.add_odid(odid("DRONE2", 49.0))
    snapshot = state.snapshot()
    assert len(snapshot["odid"]) == 2
    by_id = {e["message"]["odid"]["BasicID"][0]["UASID"]: e["message"] for e in snapshot["odid"]}
    assert by_id["DRONE1"]["odid"]["Location"]["Latitude"] == 51.0  # the latest one won


def test_heartbeats_deduplicate_by_sn() -> None:
    state = RecentState()
    state.add_heartbeat(heartbeat("SCOUT1", satellites=3))
    state.add_heartbeat(heartbeat("SCOUT1", satellites=9))
    snapshot = state.snapshot()
    assert len(snapshot["heartbeat"]) == 1
    assert snapshot["heartbeat"][0]["message"]["gnss_satellites"] == 9
    assert isinstance(snapshot["heartbeat"][0]["received_at"], float)


def test_entries_expire_after_window(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RecentState()
    clock = [1000.0]
    monkeypatch.setattr(state, "_now", lambda: clock[0])
    state.add_odid(odid("OLD", 50.0))
    state.add_heartbeat(heartbeat("OLDSCOUT"))
    clock[0] += RecentState.WINDOW / 2
    state.add_odid(odid("FRESH", 50.0))
    clock[0] += RecentState.WINDOW / 2 + 1
    snapshot = state.snapshot()
    assert [e["message"]["odid"]["BasicID"][0]["UASID"] for e in snapshot["odid"]] == ["FRESH"]
    assert snapshot["heartbeat"] == []


def test_unkeyable_messages_are_ignored() -> None:
    state = RecentState()
    state.add_odid("not json")
    state.add_odid(json.dumps({"odid": {"BasicID": []}}))
    state.add_heartbeat(json.dumps({"no_sn": True}))
    snapshot = state.snapshot()
    assert snapshot["odid"] == [] and snapshot["heartbeat"] == []


def test_state_endpoint_returns_deduplicated_state(live_server_url: str) -> None:
    for body in [odid("EP1", 50.0), odid("EP1", 50.5), heartbeat("EPSCOUT")]:
        path = "/heartbeat" if "gnss_satellites" in body else "/odid"
        req = urllib.request.Request(f"{live_server_url}{path}", data=body.encode(), method="POST")
        urllib.request.urlopen(req, timeout=5).read()
    with urllib.request.urlopen(f"{live_server_url}/state", timeout=5) as resp:
        snapshot = json.loads(resp.read())
    entries = [e for e in snapshot["odid"] if e["message"]["odid"]["BasicID"][0]["UASID"] == "EP1"]
    assert len(entries) == 1
    assert entries[0]["message"]["odid"]["Location"]["Latitude"] == 50.5
    assert any(e["message"]["sn"] == "EPSCOUT" for e in snapshot["heartbeat"])
