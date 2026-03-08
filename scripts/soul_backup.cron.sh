#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/soul_backup.py >> /root/.openclaw/workspace/memory/soul_backup_cron.log 2>&1
