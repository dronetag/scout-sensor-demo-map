# Changelog

## 1.4.0 - 2026-07-19

### Added

- **Aviation Overview**: aircraft (ADS-B / ADS-L / OGN / UAT) get their own panel on the right with the same fields as drones plus the **Flight Number** (SelfID); drones stay in the Drone Overview on the left
- **Manufacturer and model** resolved from the ornithology `registration` field, shown in drone popups and the Drone Overview (`(best guess)` marks uncertain matches)
- **Operator position** in drone popups as a Google Maps link, and an operator marker (amber controller icon) on the map while the drone's popup is open, following live updates
- **`GET /state` endpoint**: a last-5-minutes snapshot of all sensors and detections, deduplicated by sensor SN and drone serial number (UASID) with the freshest message winning — the map loads it on every (re)connect so the current airspace appears instantly
- **Batched payloads**: bodies joining several messages with `""`, `\n` or `\r\n`, or as a JSON array, are split into individual messages (HTTP and MQTT alike)
- **Compressed payloads**: gzip (recognized by magic bytes, proxy-safe) and deflate; `/` advertises `Accept-Encoding: gzip`, which makes SCOUTs enable compression automatically
- **AutoCenter on Sensor** (default on): keeps the view fitted around the latest active sensor with at least 20 km of space on each side
- **Stale markers**: drones, planes and sensors with no data for 2 minutes turn gray and recover on fresh data
- Coordinates everywhere (sensor list, all popups) with 5 decimals as **clickable Google Maps links**; timestamps in the browser's locale format
- Clicking a drone/plane in an overview list flies to it and **opens its popup** (one open popup at a time)
- Opening view zooms to the **country derived from the browser timezone** (locale as fallback)
- README: SCOUT UI forwarder configuration guide with screenshot and help-center link, architecture diagram, and a module reference — the server is split into documented modules (`ingest_http`, `ingest_mqtt`, `payload`, `bus`, `state`, `storage`, `server`) so the project doubles as a reference for ingesting SCOUT data
- Unit tests for the wire format (batching/compression) and the state snapshot

### Changed

- **AutoCenter on Drones** now defaults to **off** and only reacts to drones, not aviation traffic; focusing any target (list click or marker click) turns both autocenter modes off
- All four panels have matching pinned header bars (Configuration, Dronetag Sensors, Drone Overview, Aviation Overview); the autocenter options moved to the Configuration panel
- Drone Overview is wider, left-aligned and scrolls on its **left** edge; Aviation Overview scrolls on the right; scrollbars are clearly visible whenever a list overflows

### Fixed

- One WebSocket client dying mid-send no longer kills live updates for every other client until restart
- An open popup survives position updates: it stays open, follows its marker and refreshes its content (sensor popups used to close on every heartbeat)
- Reconnecting cleans up the previous session's markers, paths and map sources (re-adding a known source used to throw)
- Sensor `gnss_position` is no longer reversed in place, which flipped coordinates when more than one sensor was listed
- Bottom panels can no longer grow underneath the top panels and steal their clicks
