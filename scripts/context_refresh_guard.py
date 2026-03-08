#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports'
MEM_DIR = ROOT / 'memory'
SESSIONS_DIR = Path('/root/.openclaw/agents/main/sessions')
STATE = MEM_DIR / 'context_refresh_state.json'
LOG = MEM_DIR / 'context_refresh.log'

MAX_SESSION_AGE_SECONDS = 12 * 3600
MAX_LOG_SIZE_BYTES = 2 * 1024 * 1024
KEEP_SESSION_FILES = 20
KEEP_REPORT_FILES = 80

MEM_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f'[{stamp}] {msg}\n')


def trim_large_logs():
    targets = [
        ROOT / 'reports' / 'global-intel-last-run.log',
        ROOT / 'reports' / 'cyber-exchange-last-run.log',
        MEM_DIR / 'a2a_heartbeat_cron.log',
        MEM_DIR / 'a2a_heartbeat_monitor.log',
    ]
    for p in targets:
        if p.exists() and p.stat().st_size > MAX_LOG_SIZE_BYTES:
            data = p.read_text(encoding='utf-8', errors='ignore')[-200000:]
            p.write_text(data, encoding='utf-8')
            log(f'TRIM_LOG {p}')


def prune_sessions():
    if not SESSIONS_DIR.exists():
        return
    files = sorted(SESSIONS_DIR.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    now = time.time()
    kept = 0
    for f in files:
        age = now - f.stat().st_mtime
        if kept < KEEP_SESSION_FILES and age < MAX_SESSION_AGE_SECONDS:
            kept += 1
            continue
        try:
            f.unlink()
            log(f'DELETE_SESSION {f.name}')
        except Exception as e:
            log(f'WARN_SESSION {f.name} {e}')


def prune_report_snapshots():
    for pattern in ['global-intel-*.md', 'cyber-exchange-*.md']:
        files = sorted(REPORT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[KEEP_REPORT_FILES:]:
            try:
                f.unlink()
                log(f'DELETE_REPORT {f.name}')
            except Exception as e:
                log(f'WARN_REPORT {f.name} {e}')


def write_state():
    payload = {
        'last_run': time.strftime('%Y-%m-%d %H:%M:%S'),
        'session_dir': str(SESSIONS_DIR),
        'keep_sessions': KEEP_SESSION_FILES,
        'keep_reports': KEEP_REPORT_FILES,
    }
    STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    prune_sessions()
    prune_report_snapshots()
    trim_large_logs()
    write_state()
    log('REFRESH_OK')


if __name__ == '__main__':
    main()
