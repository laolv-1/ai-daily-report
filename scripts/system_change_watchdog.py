#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/root/.openclaw/workspace')
STATE = ROOT / 'memory' / 'system_change_watchdog_state.json'
WATCH = [
    ROOT / 'scripts',
    ROOT / 'memory',
    Path('/root/openclaw/skills'),
    Path('/root/.openclaw/openclaw.json'),
]
INCLUDE_SUFFIX = {'.py', '.sh', '.md', '.json'}
IGNORE_NAMES = {
    'system_change_log_state.json',
    'system_change_watchdog_state.json',
    'context_refresh.log',
    'a2a_heartbeat_monitor.log',
    'a2a_heartbeat_cron.log',
    'soul_backup.log',
    'soul_backup_cron.log',
}


def iter_files():
    for base in WATCH:
        if not base.exists():
            continue
        if base.is_file():
            yield base
            continue
        for p in sorted(base.rglob('*')):
            if not p.is_file():
                continue
            if p.name in IGNORE_NAMES:
                continue
            if p.suffix and p.suffix not in INCLUDE_SUFFIX:
                continue
            yield p


def fingerprint():
    h = hashlib.sha256()
    items = []
    for p in iter_files():
        st = p.stat()
        rel = str(p)
        row = f'{rel}|{int(st.st_mtime)}|{st.st_size}'
        items.append(row)
        h.update(row.encode('utf-8', 'ignore'))
    return h.hexdigest(), items


def load_state():
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_state(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    current_fp, items = fingerprint()
    old = load_state()
    if old.get('fingerprint') == current_fp:
        print('NO_CHANGE')
        return
    note = '自动巡检发现代码/配置/技能文件发生变化，已生成并推送最新系统变更日志。'
    subprocess.check_call(['python3', str(ROOT / 'scripts' / 'system_change_log.py'), note], cwd=str(ROOT))
    save_state({
        'fingerprint': current_fp,
        'last_push_bjt': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'tracked_items': items[-300:],
    })
    print('CHANGE_PUSHED')


if __name__ == '__main__':
    main()
