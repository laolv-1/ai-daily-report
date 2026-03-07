#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/pull_and_push_intel.py > /root/.openclaw/workspace/reports/global-intel-last-run.log 2>&1
