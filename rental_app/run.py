#!/usr/bin/env python3
"""
RentalAI local runner (mainline entry).

This is the only recommended local startup entry for the current project.
Run from project root:

    cd rental_app
    python run.py

Current product focus:
- FastAPI web product is the main product entry (not Streamlit-first).
- Product = RentAI (long-term rental main system) + ShortRentAI (short-rent module).
- ShortRentAI extends RentAI within one platform; it does not replace RentAI.

Entry responsibilities:
- `run.py`: recommended local startup entry (this file).
- `api_server.py`: main backend app entry (`api_server:app`).
- `app.py`: deployment shim.
- `app_web.py`: legacy/auxiliary Streamlit UI, not the current main entry.

Environment:
- Optional `rental_app/.env` (KEY=value lines) is auto-loaded when present
  (stdlib parser, no python-dotenv dependency).
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

# Auto-load local .env so `python run.py` works with local overrides directly.
_load_env_file(_ROOT / ".env")
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    # Ensure local imports (e.g. `config`, `api_server`) resolve consistently
    # regardless of where the command is executed from.
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
        (
            "RentalAI main web app starting\n"
            "Entry: run.py (recommended local startup)\n"
            "Backend entry: api_server.py (api_server:app)\n"
            "Main URL: http://%s:%s/  (reload=%s)"
        )
        % (host, port, reload),
        flush=True,
    )
    # Mainline runtime path: launch FastAPI from `api_server:app`.
    # This keeps local startup behavior aligned with current product architecture.
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
