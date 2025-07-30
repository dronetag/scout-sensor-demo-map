import argparse
import logging
import shutil
import subprocess
import sys

from . import server

MQTT_SERVER_BINARY = shutil.which("mosquitto")


def start_mosquitto(mosquitto_port: int) -> subprocess.Popen:
    mosquitto_cmd = [MQTT_SERVER_BINARY, "-p", str(mosquitto_port)]
    return subprocess.Popen(mosquitto_cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the server with WebSocket and MQTT support."
    )
    parser.add_argument("--http-port", type=int, default=9090, help="HTTP server port.")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument(
        "--http-local-only",
        action="store_true",
        help="Whether the http should be bind only to localhost",
    )
    parser.add_argument(
        "--mqtt-address", type=str, default="localhost", help="MQTT broker address."
    )
    parser.add_argument(
        "--mqtt-start", action="store_true", help="Start the MQTT broker on given port."
    )
    parser.add_argument("--silent", action="store_true", help="Enable silent logging.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.WARNING if args.silent else logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    mosquitto_proc = None
    if args.mqtt_start:
        if not MQTT_SERVER_BINARY:
            print("Cannot start local mosquitto instance")
            sys.exit(1)

        print("Starting local mosquitto instance")
        mosquitto_proc = start_mosquitto(args.mqtt_port)

    http_host = None
    if args.http_local_only:
        http_host = "127.0.0.1"

    try:
        server.run(
            http_port=args.http_port,
            http_host=http_host,
            mqtt_port=args.mqtt_port,
            mqtt_addr=args.mqtt_address,
        )
    finally:
        if mosquitto_proc:
            mosquitto_proc.terminate()


if __name__ == "__main__":
    main()
