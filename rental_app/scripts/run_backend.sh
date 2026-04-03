#!/usr/bin/env bash
# RentalAI — 从仓库任意 cwd 调用：切到 rental_app 后启动 run.py
set -euo pipefail
cd "$(dirname "$0")/.."
exec python run.py
