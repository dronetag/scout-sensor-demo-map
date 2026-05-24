# Scout Sensor Demo Map

Scout Sensor Demo Map is a receiving side of SCOUT data. It provides an interactive map webpage showing drone positions and receiver statuses from SCOUT sensors via HTTP and MQTT.

## Requirements

- Python 3.10+
- MQTT broker (e.g. [mosquitto](https://mosquitto.org/))

## How to point your SCOUT to Sensor Map

- Get the IP address of your local machine (Linux: `ip a`, Windows: `ipconfig`)
- Start this app: `scout-sensor-demo-map --http-port 9090`
- In your web browser, go to `http://<scout-ip>:8080`
    - Add a custom forwarder in the SCOUT UI as `http://<your-ip>:9090/odid` (click Save)
    - Add a heartbeat forwarder as `http://<your-ip>:9090/heartbeat` (click Save)
    - You can close the Scout UI now
- Open `http://localhost:9090` in your browser. The map should report "Connected" and begin receiving data.

## Installation

Make sure you have Python 3.10 or later installed (`python --version`).

### Using a virtual environment (recommended)

```sh
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
.venv\Scripts\Activate.ps1          # Windows (may require: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser)
pip install scout-sensor-demo-map-<version>.tar.gz
```

## Usage

```sh
scout-sensor-demo-map [--http-port PORT] [--mqtt-port PORT] [--mqtt-address HOST] [--mqtt-start] [--http-local-only]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--http-port` | `9090` | HTTP server port |
| `--mqtt-port` | `1883` | MQTT broker port |
| `--mqtt-address` | `localhost` | MQTT broker address |
| `--mqtt-start` | off | Start a local mosquitto instance on the given port |
| `--http-local-only` | off | Bind HTTP server to `127.0.0.1` only |
| `--debug` | off | Enable debug logging |
| `--silent` | off | Suppress all non-error logs |

## Deployment behind a reverse proxy

The server reads standard forwarded headers set by reverse proxies such as nginx or Traefik:

| Header | Purpose |
|--------|---------|
| `X-Forwarded-Host` | External hostname seen by the client |
| `X-Forwarded-Proto` | External protocol (`http` or `https`) |
| `X-Forwarded-For` | Original client IP address |
| `X-Forwarded-Prefix` | URL path prefix the proxy strips before forwarding |

When `X-Forwarded-Prefix` is set (e.g. `/map`), redirect responses and the `url()` Jinja template helper automatically include the prefix, so the app works correctly at a sub-path.

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
