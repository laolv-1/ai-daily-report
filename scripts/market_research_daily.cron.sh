#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/market_research_daily.py >> /root/.openclaw/workspace/memory/market_research_daily.cron.log 2>&1
