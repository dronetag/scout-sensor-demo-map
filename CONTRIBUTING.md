# Contributing

## Development setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install --with-deps chromium   # once, for the browser tests
```

Before opening a pull request run the linters and type-check (see the
Development section of the [README](README.md#development)):

```sh
ruff check src/
ruff format src/
pyright src/
```

## Testing

Run the whole suite with:

```sh
pytest
```

The suite has two layers — put new tests in the right one:

- **Unit tests** (no browser, milliseconds): pure server logic.
  [`tests/test_batching.py`](tests/test_batching.py) covers the SCOUT wire
  format ([`payload.py`](src/scout_sensor_demo_map/payload.py) — batching and
  compression), [`tests/test_state.py`](tests/test_state.py) covers the
  `/state` snapshot ([`state.py`](src/scout_sensor_demo_map/state.py) —
  deduplication, expiry) including one round-trip against a live server.
  Anything testable without a browser belongs here.
- **Browser tests** ([`tests/test_server.py`](tests/test_server.py),
  pytest-playwright + headless Chromium): the map page itself. The
  `live_server_url` fixture from [`tests/conftest.py`](tests/conftest.py)
  starts a real server via `server.create_app()` (without MQTT), so tests can
  `POST` synthetic messages and assert on the rendered page.

Changes to the map page ([`templates/index.jinja`](src/scout_sensor_demo_map/templates/index.jinja))
should also be exercised manually — start the server and feed it synthetic
data:

```sh
scout-sensor-demo-map --http-port 9090
curl -X POST http://localhost:9090/heartbeat -d \
  '{"sn": "TEST1", "gnss_position": [50.07, 14.46], "gnss_satellites": 9, "receivers": 1, "timestamp": 1789000000}'
curl -X POST http://localhost:9090/odid -d \
  '{"sn": "TEST1", "rssi": -70, "tech": "B4", "registration": null,
    "odid": {"BasicID": [{"UAType": 2, "IDType": 1, "UASID": "1596A300000000F"}],
             "Location": {"Latitude": 50.08, "Longitude": 14.47, "Timestamp": "2026-01-01T12:00:00"},
             "SelfID": null, "System": null, "OperatorID": null}}'
```

Two rendering caveats when verifying visually:

- headless Chromium draws overlay scrollbars — check scrollbar styling in a
  headed browser
- ODID timestamps are naive UTC strings; verify timestamp rendering with a
  non-UTC browser timezone

## Changelog

Every user-visible change (feature, behavior change, fix) gets an entry in
[`CHANGELOG.md`](CHANGELOG.md) in the same commit or pull request as the
change itself. Purely internal work (refactoring, CI, tests) does not need
one.

- Add the entry under the section for the **next unreleased version** at the
  top of the file — create the section if it does not exist yet:

  ```markdown
  ## X.Y.Z - unreleased
  ```

- Use the existing `### Added` / `### Changed` / `### Fixed` groups.
- Write for the user of the map, not for the reader of the diff: say what
  changed on the page or on the wire, not which function was edited.

## Releasing

The package version is stamped from the git tag at release time (the
`99.99` in [`__version__.py`](src/scout_sensor_demo_map/__version__.py) is a
placeholder). To release:

1. Make sure the changelog section for the version is complete, and replace
   `unreleased` with the release date.
2. Tag: `git tag vX.Y.Z && git push origin main vX.Y.Z`.
3. After the sdist is published, bump the `python3-scout-sensor-demo-map`
   recipe in meta-dronetag so the SCOUT image ships the new version.
