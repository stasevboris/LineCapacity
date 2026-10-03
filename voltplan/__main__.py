from __future__ import annotations

import argparse
import threading
import time
import webbrowser

import uvicorn

from .app import create_app
from .config import HOST, PORT


def open_when_ready(server: uvicorn.Server, url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.1)
    if server.started:
        webbrowser.open(url)


def main() -> None:
    parser = argparse.ArgumentParser(prog="voltplan", description="Сервер VoltPlan")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true", help="открыть браузер")
    args = parser.parse_args()
    server = uvicorn.Server(uvicorn.Config(create_app(), host=args.host, port=args.port, log_level="warning"))
    if args.open:
        url = f"http://{args.host}:{args.port}/"
        threading.Thread(target=open_when_ready, args=(server, url), daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
