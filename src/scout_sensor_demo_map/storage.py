"""Optional JSONL persistence of every ingested message, rotated daily."""

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import IO

logger = logging.getLogger("dt.receiver.map")


class MessageStorage:
    def __init__(self, storage_dir: Path) -> None:
        storage_dir.mkdir(parents=True, exist_ok=True)
        self._storage_dir = storage_dir
        self._date = date.today()
        self._odid: IO[str] = open(self._odid_path(), "a")
        self._heartbeat: IO[str] = open(self._heartbeat_path(), "a")
        logger.info("Storage opened at %s", storage_dir)

    def _odid_path(self) -> Path:
        return self._storage_dir / f"telemetry_{self._date.isoformat()}.jsonl"

    def _heartbeat_path(self) -> Path:
        return self._storage_dir / f"heartbeat_{self._date.isoformat()}.jsonl"

    def _rotate_if_needed(self) -> None:
        today = date.today()
        if today == self._date:
            return
        self._odid.close()
        self._heartbeat.close()
        self._date = today
        self._odid = open(self._odid_path(), "a")
        self._heartbeat = open(self._heartbeat_path(), "a")
        logger.info("Storage rotated to %s", self._date.isoformat())

    def _write(self, file: IO[str], data: str, source: str) -> None:
        try:
            parsed: object = json.loads(data)
        except json.JSONDecodeError:
            parsed = data
        record = json.dumps({"received_at": time.time(), "source": source, "data": parsed})
        file.write(record + "\n")
        file.flush()

    def write_odid(self, data: str, source: str) -> None:
        self._rotate_if_needed()
        self._write(self._odid, data, source)

    def write_heartbeat(self, data: str, source: str) -> None:
        self._rotate_if_needed()
        self._write(self._heartbeat, data, source)

    def close(self) -> None:
        self._odid.close()
        self._heartbeat.close()
