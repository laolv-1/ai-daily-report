#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/system_change_watchdog.py >> /root/.openclaw/workspace/memory/system_change_watchdog.log 2>&1
