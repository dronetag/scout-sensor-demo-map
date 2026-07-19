"""Last-minutes snapshot of the airspace for the /state bootstrap endpoint."""

import json
import logging
import time

logger = logging.getLogger("dt.receiver.map")


class RecentState:
    """The freshest message per sensor (sn) and per detection (UASID) from the
    last WINDOW seconds, so a newly opened map starts populated instantly."""

    WINDOW = 300.0  # seconds

    def __init__(self) -> None:
        self._detections: dict[str, tuple[float, object]] = {}
        self._heartbeats: dict[str, tuple[float, object]] = {}

    _now = staticmethod(time.time)  # replaceable in tests

    def _prune(self, store: dict[str, tuple[float, object]]) -> None:
        deadline = self._now() - self.WINDOW
        for key in [key for key, (received_at, _) in store.items() if received_at < deadline]:
            del store[key]

    def add_odid(self, message: str) -> None:
        try:
            parsed = json.loads(message)
            uasid = parsed["odid"]["BasicID"][0]["UASID"]  # the map keys detections the same way
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            return  # not a detection the map could show - nothing to remember
        if uasid:
            self._detections[str(uasid)] = (self._now(), parsed)

    def add_heartbeat(self, message: str) -> None:
        try:
            parsed = json.loads(message)
            sn = parsed["sn"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return
        if sn:
            self._heartbeats[str(sn)] = (self._now(), parsed)

    def snapshot(self) -> dict[str, list[object]]:
        self._prune(self._detections)
        self._prune(self._heartbeats)
        return {
            "heartbeat": [
                {"received_at": received_at, "message": payload}
                for received_at, payload in self._heartbeats.values()
            ],
            "odid": [
                {"received_at": received_at, "message": payload}
                for received_at, payload in self._detections.values()
            ],
        }


recent_state = RecentState()
