#!/usr/bin/env python3
import datetime as dt
import json
import subprocess
from pathlib import Path

import paramiko
import requests

from github_sync_helper import copy_into_repo, commit_and_push, dated_rel_path

ROOT = Path('/root/.openclaw/workspace')
REPORTS = ROOT / 'reports'
MEMORY = ROOT / 'memory'
WIN_HOST = '100.89.160.67'
WIN_USER = 'Administrator'
WIN_PASSWORD = 'As1231'
REMOTE_BASE = 'D:/来财/系统更新日志'
MODEL_BASE = 'http://74.48.182.210:8317/v1'
MODEL_KEY = 'xDjn0xIm6ztThd8pSexN8CmCRttLtt8T'
MODEL_NAME = 'lck/gpt-5.4'
MAX_FILES = 12


def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError((p.stdout or '') + '\n' + (p.stderr or ''))
    return (p.stdout or '').strip()


def changed_files(limit=MAX_FILES):
    lines = run(['git', 'status', '--short']).splitlines()
    cleaned = []
    for line in lines:
        if not line.strip():
            continue
        path = line[3:].strip()
        if not path:
            continue
        cleaned.append(path)
    return cleaned[:limit]


def file_mtime(path: Path) -> str:
    if not path.exists():
        return '未落盘'
    ts = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone(dt.timedelta(hours=8)))
    return ts.strftime('%Y-%m-%d %H:%M:%S BJT')


def diff_for(path: str) -> str:
    try:
        if path.startswith('/root/'):
            p = Path(path)
            if not p.exists():
                return f'文件不存在：{path}'
            text = p.read_text(encoding='utf-8', errors='ignore')
            return text[:4000]
        diff = run(['git', 'diff', '--', path], check=False)
        if diff.strip():
            return diff[:5000]
        p = ROOT / path
        if p.exists():
            return p.read_text(encoding='utf-8', errors='ignore')[:4000]
        return f'文件不存在：{path}'
    except Exception as e:
        return f'无法读取差异：{path} | {e}'


def summarize_change(path: str, content: str) -> str:
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是系统变更审计官。你的任务是把代码差异翻译成主公一眼能看懂的人话。'
                    '只输出一句中文短句，不要解释过程，不要说可能，也不要输出 Markdown 列表。'
                    '输出风格必须像：增加了 Polymarket 强制等待 15 秒的逻辑；修复了 Win10 中文路径桥接；加入了双因子硬校验。'
                    '如果是状态文件或日志文件，就简洁说明它记录了什么运行状态。'
                )
            },
            {
                'role': 'user',
                'content': json.dumps({'file': path, 'content': content[:3500]}, ensure_ascii=False)
            }
        ],
        'temperature': 0.2,
    }
    url = MODEL_BASE.rstrip('/') + '/chat/completions'
    r = requests.post(url, headers={'Authorization': f'Bearer {MODEL_KEY}'}, json=prompt, timeout=90)
    r.raise_for_status()
    text = r.json()['choices'][0]['message']['content'].strip()
    return text.replace('\n', ' ').strip(' -')


def collect_entries(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    entries = []
    for rel in changed_files():
        p = ROOT / rel
        human = summarize_change(rel, diff_for(rel))
        entries.append({
            'time': file_mtime(p),
            'file': rel,
            'summary': human,
        })
    if extra_notes.strip():
        entries.append({
            'time': now.strftime('%Y-%m-%d %H:%M:%S BJT'),
            'file': '本次补充说明',
            'summary': extra_notes.strip(),
        })
    return entries


def build_log(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    date_str = now.strftime('%Y-%m-%d')
    entries = collect_entries(extra_notes)
    lines = [
        f'# 系统变更日志｜{date_str}',
        '',
        '## 今日变更摘要',
        '以下内容已从真实代码差异与文件变更中翻译为人话：',
        '',
    ]
    if not entries:
        lines.append('- [无变更] 今日未发现需要上报的核心改动。')
    else:
        for item in entries:
            lines.append(f"- [{item['time']}] `{item['file']}`：{item['summary']}")
    lines += [
        '',
        '## 最近提交',
        '```',
        run(['git', 'log', '-5', '--pretty=format:%h %s'], check=False) or '无',
        '```',
    ]
    return '\n'.join(lines)


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


def sync_to_github(local_file: Path) -> dict:
    filename = local_file.name
    rel = dated_rel_path('system-change-logs', filename)
    copy_into_repo(local_file, rel)
    return commit_and_push(f'系统变更日志: {filename}')


def main(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    file = REPORTS / f'{now.strftime("%Y-%m-%d")}_update_log.md'
    file.parent.mkdir(parents=True, exist_ok=True)
    text = build_log(extra_notes)
    file.write_text(text, encoding='utf-8')
    remote_file, size = push_to_win10(file)
    github = sync_to_github(file)
    state = {
        'last_push_bjt': now.strftime('%Y-%m-%d %H:%M:%S'),
        'remote_file': remote_file,
        'size': size,
        'github': github,
    }
    (MEMORY / 'system_change_log_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    note = sys.argv[1] if len(sys.argv) > 1 else ''
    main(note)
