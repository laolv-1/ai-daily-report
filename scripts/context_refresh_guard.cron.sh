#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/context_refresh_guard.py >> /root/.openclaw/workspace/memory/context_refresh_guard.cron.log 2>&1
