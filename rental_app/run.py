#!/usr/bin/env python3
"""
RentalAI — single local entry (Phase4).

Starts FastAPI + Phase3 static web on one port. Run from anywhere:

    cd rental_app
    python run.py

Environment: optional `rental_app/.env` (KEY=value lines) is loaded automatically
if the file exists (stdlib parser, no python-dotenv dependency).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val


_load_env_file(_ROOT / ".env")
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    import uvicorn

    from config import get_bind_host, get_bind_port, get_effective_debug, get_uvicorn_reload

    if get_effective_debug():
        logging.basicConfig(level=logging.DEBUG)
    host = get_bind_host()
    port = get_bind_port()
    reload = get_uvicorn_reload()
    print(
        "RentalAI starting — http://%s:%s/  (reload=%s)" % (host, port, reload),
        flush=True,
    )
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
