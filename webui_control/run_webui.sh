#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
exec python3 -m uvicorn webui_control.app:app --host 0.0.0.0 --port 8090
