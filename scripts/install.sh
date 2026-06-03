#!/bin/bash
# Installs scout-sensor-demo-map into a local venv and registers it as a
# system-wide systemd service running as the current user.
# Run with: bash scripts/install.sh   (sudo is invoked internally for systemd)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SCRIPT_DIR/venv"
STORAGE_DIR="$SCRIPT_DIR/storage"
SERVICE_NAME="scout-sensor-demo-map"
CURRENT_USER="$(whoami)"

echo "=== Scout Sensor Demo Map — installer ==="
echo "  Project : $PROJECT_DIR"
echo "  Venv    : $VENV_DIR"
echo "  Storage : $STORAGE_DIR"
echo "  Service : $SERVICE_NAME"
echo "  User    : $CURRENT_USER"
echo

# ── 1. Virtual environment & package ──────────────────────────────────────────
echo "[1/4] Creating virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install "$PROJECT_DIR"
echo "      Package installed."

# ── 2. Storage directory ───────────────────────────────────────────────────────
echo "[2/4] Creating storage directory..."
mkdir -p "$STORAGE_DIR"
echo "      $STORAGE_DIR"

# ── 3. Systemd service unit ────────────────────────────────────────────────────
echo "[3/4] Writing systemd unit /etc/systemd/system/${SERVICE_NAME}.service ..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Scout Sensor Demo Map
Documentation=https://github.com/dronetag/scout-sensor-demo-map
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${VENV_DIR}/bin/scout-sensor-demo-map --storage ${STORAGE_DIR}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── 4. Enable & start ─────────────────────────────────────────────────────────
echo "[4/4] Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo
echo "=== Done! ==="
echo
echo "Service status  : systemctl status $SERVICE_NAME"
echo "Follow logs     : journalctl -u $SERVICE_NAME -f"
echo "Stop service    : sudo systemctl stop $SERVICE_NAME"
echo "Disable service : sudo systemctl disable $SERVICE_NAME"
echo "Storage files   : $STORAGE_DIR/heartbeat_YYYY-MM-DD.jsonl"
echo "                  $STORAGE_DIR/telemetry_YYYY-MM-DD.jsonl"
echo
echo "Map UI          : http://localhost:9090"
echo "Scout ODID URL  : http://<your-ip>:9090/odid"
echo "Scout HB URL    : http://<your-ip>:9090/heartbeat"
