from __future__ import annotations

import argparse
import contextlib
import http.server
import os
import socket
import sys
from pathlib import Path


def _detect_lan_ip() -> str:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a generated UAV static site over HTTP.")
    parser.add_argument("--site-dir", required=True, help="Static site directory")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    site_dir = Path(args.site_dir).resolve()
    if not site_dir.exists():
        raise FileNotFoundError(f"Site dir not found: {site_dir}")

    os.chdir(site_dir)
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer((args.host, args.port), handler)

    lan_ip = _detect_lan_ip()
    print(f"serving: {site_dir}")
    print(f"local:  http://127.0.0.1:{args.port}/")
    print(f"intranet: http://{lan_ip}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
