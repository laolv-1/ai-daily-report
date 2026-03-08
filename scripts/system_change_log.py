#!/usr/bin/env python3
import datetime as dt
import json
import subprocess
from pathlib import Path

import paramiko

ROOT = Path('/root/.openclaw/workspace')
REPORTS = ROOT / 'reports'
MEMORY = ROOT / 'memory'
WIN_HOST = '100.89.160.67'
WIN_USER = 'Administrator'
WIN_PASSWORD = 'As1231'
REMOTE_BASE = 'D:/来财/系统更新日志'
DEFAULT_SKILLS = [
    Path('/root/openclaw/skills/skill_context_refresh.md'),
    Path('/root/openclaw/skills/skill_tool_roi_scheduler.md'),
]
DEFAULT_FILES = [
    ROOT / 'scripts' / 'soul_backup.py',
    ROOT / 'scripts' / 'soul_backup.cron.sh',
    ROOT / 'scripts' / 'system_change_log.py',
    ROOT / 'scripts' / 'system_change_watchdog.py',
    ROOT / 'scripts' / 'cyber_exchange_audit.py',
    Path('/root/.openclaw/openclaw.json'),
]


def run(cmd):
    return subprocess.check_output(cmd, cwd=str(ROOT), text=True, stderr=subprocess.STDOUT).strip()


def collect_git_status():
    try:
        return run(['git', 'status', '--short'])
    except Exception as e:
        return f'[git status unavailable] {e}'


def collect_recent_commits(limit=5):
    try:
        return run(['git', 'log', f'-{limit}', '--pretty=format:%h %s'])
    except Exception as e:
        return f'[git log unavailable] {e}'


def build_log(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    date_str = now.strftime('%Y-%m-%d')
    body = [f'# 系统变更日志｜{date_str}', '', '## 今日概况', '自动记录本体与蜂群的代码改动、配置修改、新技能固化。', '']
    body += ['## 新技能固化']
    found = False
    for p in DEFAULT_SKILLS:
        if p.exists():
            found = True
            body.append(f'- {p}')
    if not found:
        body.append('- 无')
    body += ['', '## 关键物理文件']
    found_files = False
    for p in DEFAULT_FILES:
        if p.exists():
            found_files = True
            body.append(f'- {p}')
    if not found_files:
        body.append('- 无')
    body += ['', '## 近期提交', '```', collect_recent_commits(), '```', '', '## 当前工作区状态', '```', collect_git_status(), '```']
    if extra_notes.strip():
        body += ['', '## 本次补充说明', extra_notes.strip()]
    return '\n'.join(body)


def push_to_win10(local_file: Path):
    remote_file = f'{REMOTE_BASE}/{local_file.name}'
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=WIN_HOST, username=WIN_USER, password=WIN_PASSWORD, timeout=10, banner_timeout=10, auth_timeout=10)
    try:
        cmd = f'powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path \'{REMOTE_BASE}\' | Out-Null"'
        stdin, stdout, stderr = cli.exec_command(cmd, timeout=20)
        _ = stdout.read().decode('utf-8', 'ignore')
        err = stderr.read().decode('utf-8', 'ignore')
        if err.strip():
            raise RuntimeError(err)
        sftp = cli.open_sftp()
        try:
            sftp.put(str(local_file), remote_file)
            with sftp.open(remote_file, 'r') as f:
                data = f.read()
                if isinstance(data, bytes):
                    data = data.decode('utf-8', 'ignore')
        finally:
            sftp.close()
    finally:
        cli.close()
    return remote_file, len(data)


def main(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    file = REPORTS / f'{now.strftime("%Y-%m-%d")}_update_log.md'
    file.parent.mkdir(parents=True, exist_ok=True)
    text = build_log(extra_notes)
    file.write_text(text, encoding='utf-8')
    remote_file, size = push_to_win10(file)
    state = {
        'last_push_bjt': now.strftime('%Y-%m-%d %H:%M:%S'),
        'remote_file': remote_file,
        'size': size,
    }
    (MEMORY / 'system_change_log_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    note = sys.argv[1] if len(sys.argv) > 1 else ''
    main(note)
