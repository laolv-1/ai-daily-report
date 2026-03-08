#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/cyber_exchange_audit.py >> /root/.openclaw/workspace/reports/cyber-exchange-last-run.log 2>&1
