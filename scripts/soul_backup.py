#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path

import paramiko

from github_sync_helper import commit_and_push, copy_into_repo, dated_rel_path

ROOT = Path('/root/.openclaw/workspace')
WIN_HOST = '100.89.160.67'
WIN_USER = 'Administrator'
WIN_PASSWORD = 'As1231'
BASE_DIR = 'D:/来财/灵魂备份'
LOCAL_LOG = ROOT / 'memory' / 'soul_backup.log'
LOCAL_STATE = ROOT / 'memory' / 'soul_backup_state.json'

FILES_TO_CAPTURE = [
    ROOT / 'SOUL.md',
    ROOT / 'USER.md',
    ROOT / 'IDENTITY.md',
    ROOT / 'AGENTS.md',
    ROOT / 'TOOLS.md',
    ROOT / 'MEMORY.md',
    ROOT / 'memory' / '2026-03-07.md',
    ROOT / 'memory' / '2026-03-08.md',
    Path('/root/openclaw/skills/skill_context_refresh.md'),
    Path('/root/openclaw/skills/skill_tool_roi_scheduler.md'),
]


def log(msg: str) -> None:
    LOCAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with LOCAL_LOG.open('a', encoding='utf-8') as f:
        f.write(f'[{stamp}] {msg}\n')


def build_backup_text() -> str:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    lines = [
        f'# 来财灵魂备份 | {now.strftime("%Y-%m-%d %H:%M:%S BJT")}',
        '',
        '## 备份清单',
    ]
    for p in FILES_TO_CAPTURE:
        lines.append(f'- {p}')
    lines.append('')
    for p in FILES_TO_CAPTURE:
        lines.append(f'--- FILE: {p} ---')
        if p.exists():
            try:
                lines.append(p.read_text(encoding='utf-8', errors='ignore'))
            except Exception as e:
                lines.append(f'[READ_ERROR] {e}')
        else:
            lines.append('[MISSING]')
        lines.append('')
    return '\n'.join(lines)


def push_to_win10(text: str):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    date_dir = now.strftime('%Y-%m-%d')
    remote_dir = f'{BASE_DIR}/{date_dir}'
    remote_file = f'{remote_dir}/laicai-soul-backup-{now.strftime("%Y%m%d-%H%M%S")}.md'
    local_tmp = ROOT / 'memory' / '_soul_backup_tmp.md'
    local_tmp.write_text(text, encoding='utf-8')

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=WIN_HOST, username=WIN_USER, password=WIN_PASSWORD, timeout=12, banner_timeout=12, auth_timeout=12)
    try:
        cmd = f'powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path \'{remote_dir}\' | Out-Null"'
        stdin, stdout, stderr = cli.exec_command(cmd, timeout=20)
        _ = stdout.read().decode('utf-8', 'ignore')
        err = stderr.read().decode('utf-8', 'ignore')
        if err.strip():
            raise RuntimeError(err)
        sftp = cli.open_sftp()
        try:
            sftp.put(str(local_tmp), remote_file)
            with sftp.open(remote_file, 'r') as f:
                data = f.read()
                if isinstance(data, bytes):
                    data = data.decode('utf-8', 'ignore')
        finally:
            sftp.close()
    finally:
        cli.close()
        local_tmp.unlink(missing_ok=True)
    return remote_file, len(data)


def sync_to_github(text: str) -> dict:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    tmp = ROOT / 'memory' / '_soul_backup_github.md'
    tmp.write_text(text, encoding='utf-8')
    try:
        rel = dated_rel_path('soul-backups', f'laicai-soul-backup-{now.strftime("%Y%m%d-%H%M%S")}.md')
        copy_into_repo(tmp, rel)
        return commit_and_push(f'备份: {now.strftime("%Y-%m-%d %H:%M:%S BJT")}')
    finally:
        tmp.unlink(missing_ok=True)


def write_state(remote_file: str, size: int, github: dict | None = None) -> None:
    payload = {
        'last_backup_bjt': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'remote_file': remote_file,
        'size': size,
        'github': github or {},
    }
    LOCAL_STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    text = build_backup_text()
    remote_file, size = push_to_win10(text)
    github = sync_to_github(text)
    write_state(remote_file, size, github)
    log(f'BACKUP_OK remote={remote_file} size={size} github={json.dumps(github, ensure_ascii=False)}')
    print(json.dumps({'remote_file': remote_file, 'size': size, 'github': github}, ensure_ascii=False))


if __name__ == '__main__':
    main()
