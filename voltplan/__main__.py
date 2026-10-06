from __future__ import annotations

import argparse
import threading
import time
import webbrowser

import uvicorn

from .accounts import Site
from .app import create_app
from .config import DATA_DIR, HOST, PORT
from .consultant import key_source


def open_when_ready(server: uvicorn.Server, url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.1)
    if server.started:
        webbrowser.open(url)


def make_admin(email: str) -> str:
    site = Site(DATA_DIR)
    try:
        user = site.users.find(email)
        if user is None:
            return f"Пользователь {email} не найден: сначала зарегистрируйтесь на сайте"
        with site.store.writing(site.store.work) as db:
            db.execute("UPDATE profiles SET is_admin = 1 WHERE user_id = ?", (user.id,))
        site.store.audit(user.id, "права администратора выданы из командной строки", user.email)
        return f"Пользователь {user.email} теперь администратор"
    finally:
        site.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="voltplan", description="Сервер VoltPlan")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--open", action="store_true", help="открыть браузер")
    parser.add_argument("--make-admin", metavar="EMAIL", help="выдать права администратора пользователю")
    args = parser.parse_args()
    if args.make_admin:
        print(make_admin(args.make_admin))
        return
    server = uvicorn.Server(uvicorn.Config(create_app(), host=args.host, port=args.port, log_level="warning"))
    url = f"http://{args.host}:{args.port}/"
    print(f"VoltPlan: {url}", flush=True)
    print(key_source(DATA_DIR), flush=True)
    if args.open:
        threading.Thread(target=open_when_ready, args=(server, url), daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
