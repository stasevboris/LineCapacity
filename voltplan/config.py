from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT = PACKAGE_DIR.parent
WEB = PACKAGE_DIR / "web"
DATABASE = ROOT / "data" / "DataBase"
SCHEMES = ROOT / "schemes"
LOGS = ROOT / "logs"
HOST = "127.0.0.1"
PORT = 8000
