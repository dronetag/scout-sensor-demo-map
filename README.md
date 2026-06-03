# Scout Sensor Demo Map

Scout Sensor Demo Map is a receiving side of SCOUT data. It provides an interactive map webpage showing drone positions and receiver statuses from SCOUT sensors via HTTP and MQTT.

## Requirements

- Python 3.10+
- MQTT broker (e.g. [mosquitto](https://mosquitto.org/))

## How to point your SCOUT to the Sensor Map

### 1 — Find your machine's local IP address

```sh
ip a          # Linux — look for the inet address on your LAN interface (e.g. eth0, wlan0)
ipconfig      # Windows
```

Example result: `192.168.1.42`

### 2 — Start the map server

```sh
scout-sensor-demo-map --http-port 9090
```

### 3 — Configure the SCOUT in its web interface

Open `http://<scout-ip>:8080` in your browser (replace `<scout-ip>` with the IP printed on your SCOUT device or shown in your router's device list).

In the SCOUT management UI add the following forwarders — replace `<your-ip>` with the address from step 1:

| Forwarder type | URL to enter |
|----------------|--------------|
| **ODID / telemetry** | `http://<your-ip>:9090/odid` |
| **Heartbeat** | `http://<your-ip>:9090/heartbeat` |

Click **Save** after each entry.

### 4 — Open the map

Navigate to `http://localhost:9090` in your browser. The status indicators should turn green ("Connected") and drone positions will start appearing as data arrives.

---

## Installation

Make sure you have Python 3.10 or later installed (`python --version`).

### Using a virtual environment (recommended)

```sh
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
.venv\Scripts\Activate.ps1          # Windows (may require: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser)
pip install scout-sensor-demo-map-<version>.tar.gz
```

### Automated install as a systemd service (Linux)

The `scripts/install.sh` script installs the package into a local venv and registers a system-wide systemd service that starts automatically on boot.

```sh
bash scripts/install.sh
```

What the script does:
1. Creates `scripts/venv/` and installs the package there.
2. Creates `scripts/storage/` for JSONL log files.
3. Writes `/etc/systemd/system/scout-sensor-demo-map.service` (requires `sudo`).
4. Runs `systemctl enable --now scout-sensor-demo-map`.

The service runs as the **current user** (the one who executes the script).

Useful commands after installation:

```sh
systemctl status scout-sensor-demo-map       # check running state
journalctl -u scout-sensor-demo-map -f       # follow live logs
sudo systemctl stop scout-sensor-demo-map    # stop
sudo systemctl disable scout-sensor-demo-map # remove from autostart
```

---

## Usage

```sh
scout-sensor-demo-map [--http-port PORT] [--mqtt-port PORT] [--mqtt-address HOST] [--mqtt-start] [--http-local-only] [--storage DIR]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--http-port` | `9090` | HTTP server port |
| `--mqtt-port` | `1883` | MQTT broker port |
| `--mqtt-address` | `localhost` | MQTT broker address |
| `--mqtt-start` | off | Start a local mosquitto instance on the given port |
| `--http-local-only` | off | Bind HTTP server to `127.0.0.1` only |
| `--storage DIR` | off | Directory to persist received messages as JSONL files |
| `--debug` | off | Enable debug logging |
| `--silent` | off | Suppress all non-error logs |

### Message storage (`--storage`)

When `--storage <dir>` is provided the server appends every received message to two JSONL files inside that directory:

| File | Contents |
|------|----------|
| `telemetry_YYYY-MM-DD.jsonl` | Drone ODID / telemetry messages (HTTP `POST /odid` and MQTT topic `odid`) |
| `heartbeat_YYYY-MM-DD.jsonl` | Sensor heartbeat messages (HTTP `POST /heartbeat` and MQTT topic `heartbeat`) |

A new pair of files is created automatically at midnight, so each calendar day has its own logs.

Each line is a JSON object with three fields:

```json
{"received_at": 1748908800.123, "source": "http", "data": { ... }}
```

| Field | Description |
|-------|-------------|
| `received_at` | Unix timestamp (seconds, float) when the message was received |
| `source` | `"http"` or `"mqtt"` |
| `data` | Parsed JSON payload; raw string if the payload was not valid JSON |

The directory is created automatically if it does not exist.

Example:

```sh
scout-sensor-demo-map --storage /var/log/scout-map
```

---

## Deployment behind a reverse proxy

The server reads standard forwarded headers set by reverse proxies such as nginx or Traefik:

| Header | Purpose |
|--------|---------|
| `X-Forwarded-Host` | External hostname seen by the client |
| `X-Forwarded-Proto` | External protocol (`http` or `https`) |
| `X-Forwarded-For` | Original client IP address |
| `X-Forwarded-Prefix` | URL path prefix the proxy strips before forwarding |

When `X-Forwarded-Prefix` is set (e.g. `/map`), redirect responses and the `url()` Jinja template helper automatically include the prefix, so the app works correctly at a sub-path.

---

## Development

### Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Code quality

```sh
ruff check src/            # lint
ruff format src/           # format
pyright src/               # strict type-check
```

### Testing

Tests use [pytest-playwright](https://playwright.dev/python/) and require a Chromium browser. Install it once:

```sh
playwright install --with-deps chromium
```

Then run the full test suite:

```sh
pytest
```

The tests start a local aiohttp server (no MQTT required) and use a headless Chromium browser to verify:

- the page renders with the map and UI controls visible
- both WebSocket endpoints (`/ws/odid` and `/ws/heartbeat`) reach the "Connected" state
