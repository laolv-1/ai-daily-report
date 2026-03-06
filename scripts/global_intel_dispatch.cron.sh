#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
/usr/bin/python3 /root/.openclaw/workspace/scripts/global_intel_dispatch.py > /root/.openclaw/workspace/reports/global-intel-last-run.log 2>&1
