#!/usr/bin/env python3
import datetime as dt
import json
import re
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
MODEL_NAME = 'lck/gpt-5.2-codex'
MAX_FILES = 8
MAX_DIFF_CHARS = 6000
BLACKLIST_PHRASES = [
    '更新了逻辑', '修改了配置', '优化了代码', '更改了状态', '本次变更涉及',
    '关键标记', '运行状态变化', '更新了文档', '做了调整', '调整了逻辑',
    'requests.get(', 'timeout=', 'NOISE_PREFIXES', 'plugins/'
]
CORE_ROOT_FILES = {'.gitignore', '.env', 'package.json', 'pnpm-lock.yaml'}
CORE_SUFFIXES = ('.py', '.sh', '.json', '.md')
NOISE_PREFIXES = ('memory/', 'reports/', 'github_sync/', '.openclaw/', 'tmp_', 'memory-lancedb-pro/')
NOISE_SUFFIXES = ('.log', '.jsonl', '.out', '.draft')


def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError((p.stdout or '') + '\n' + (p.stderr or ''))
    return (p.stdout or '').strip()


def is_allowed_path(path: str) -> bool:
    if not path or path.endswith('/'):
        return False
    if any(path.startswith(prefix) for prefix in NOISE_PREFIXES):
        return False
    if path.endswith(NOISE_SUFFIXES):
        return False
    if path in CORE_ROOT_FILES:
        return True
    if path.startswith('scripts/') and path.endswith(CORE_SUFFIXES):
        return True
    if path.startswith('plugins/') and path.endswith(CORE_SUFFIXES) and '/skill/' not in path:
        return True
    if '/' not in path and path.endswith(('.json', '.env')):
        return True
    return False


def target_commit(rev: str | None = None) -> str:
    return (rev or 'HEAD').strip()


def commit_subject(rev: str) -> str:
    return run(['git', 'show', '-s', '--format=%s', rev], check=False) or '无提交说明'


def commit_time_bjt(rev: str) -> str:
    ts = run(['git', 'show', '-s', '--format=%ct', rev], check=False).strip()
    if not ts.isdigit():
        return '未知时间'
    dt_obj = dt.datetime.fromtimestamp(int(ts), dt.timezone(dt.timedelta(hours=8)))
    return dt_obj.strftime('%Y-%m-%d %H:%M:%S BJT')


def commit_files(rev: str):
    out = run(['git', 'show', '--name-only', '--format=', rev], check=False)
    names = []
    for line in out.splitlines():
        line = line.strip()
        if line and line not in names and is_allowed_path(line):
            names.append(line)
    names.sort(key=lambda p: (0 if p.startswith('scripts/') else 1, p))
    return names[:MAX_FILES]


def commit_diff_for(rev: str, path: str) -> str:
    text = run(['git', 'show', rev, '--', path], check=False)
    return text[:MAX_DIFF_CHARS] if text else ''


def extract_value_changes(diff_text: str):
    removed = []
    added = []
    for raw in diff_text.splitlines():
        if raw.startswith(('---', '+++', '@@', 'diff --git', 'index ')):
            continue
        if raw.startswith('-'):
            removed.append(raw[1:].strip())
        elif raw.startswith('+'):
            added.append(raw[1:].strip())
    pairs = []
    for old in removed[:40]:
        for new in added[:40]:
            m1 = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)', old)
            m2 = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)', new)
            if m1 and m2 and m1.group(1) == m2.group(1) and m1.group(2) != m2.group(2):
                pairs.append((m1.group(1), m1.group(2), m2.group(2)))
                break
    return pairs[:3]


def meaningful_lines(diff_text: str, limit: int = 4):
    out = []
    for raw in diff_text.splitlines():
        if raw.startswith(('+++', '---', '@@', 'diff --git', 'index ')):
            continue
        if raw.startswith('+') or raw.startswith('-'):
            line = raw[1:].strip()
            if not line:
                continue
            out.append(line)
        if len(out) >= limit:
            break
    return out


def fallback_summary(path: str, content: str) -> str:
    pairs = extract_value_changes(content)
    if path == 'scripts/market_research_daily.py' and pairs:
        key, old, new = pairs[0]
        if key == 'r':
            return f'修改了市场调研脚本，将海外数据抓取的超时等待时间从 {old.replace("requests.get(url, headers=headers, timeout=", "").replace(")", "")}秒 延长到 {new.replace("requests.get(url, headers=headers, timeout=", "").replace(")", "")}秒，降低 Reddit 请求卡死的概率。'
    if path == 'scripts/system_change_log.py' and 'plugins/' in content:
        return '修改了系统变更日志的噪音过滤规则，将 plugins/ 从黑名单中移除，这样插件目录的核心改动以后也能被正常记录。'
    if path == 'scripts/soul_backup.py' and pairs:
        key, old, new = pairs[0]
        return f'修改了灵魂备份脚本，将 {key} 的连接等待时间从 {old} 秒延长到 {new} 秒，减少跨网推送时的超时失败。'
    if pairs:
        key, old, new = pairs[0]
        return f'修改了 {path} 的参数设置，将 {key} 从 {old} 调整为 {new}。'
    lines = meaningful_lines(content, limit=3)
    if lines:
        core = lines[0]
        if len(core) > 120:
            core = core[:117] + '...'
        return f'修改了 {path}，新增的核心动作是：{core}'
    return f'修改了 {path}，但当前差异片段不足，建议结合该提交继续复盘。'


def sanitize_summary(text: str, path: str, content: str) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip(' -：:')
    if not text:
        return fallback_summary(path, content)
    for bad in BLACKLIST_PHRASES:
        if bad in text:
            return fallback_summary(path, content)
    if len(text) < 8:
        return fallback_summary(path, content)
    return text


def summarize_change(path: str, content: str) -> str:
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是一个冷酷的战术分析师，但写给主公看的必须是业务大白话。你只能根据真实 git diff 输出一句纯中文结论。'
                    '最终输出绝对禁止原样抛出英文代码长串、函数调用表达式、变量赋值片段。'
                    '你必须把改动翻译成：修改了什么文件的什么功能 + 把什么数值从A变成了B + 目的是什么。'
                    '严禁输出：更新了逻辑、修改了配置、优化了代码、更改了状态、本次变更涉及、关键标记。'
                    '如果 diff 里存在数值变化，必须写出“从多少改到多少”，并补一句业务目的。'
                    '如果 diff 里是在调整过滤名单、白名单、开关或路径，必须翻译成“为了让什么能被记录/屏蔽/通过”。'
                    '如果实在无法翻译，宁可只保留最短的中文业务解释，也不要贴英文源码。'
                    '正确示范1：scripts/market_research_daily.py -> 修改了市场调研脚本，将网络请求的超时等待时间从25秒延长到28秒，防止抓取海外数据时卡死。'
                    '正确示范2：scripts/system_change_log.py -> 修改了系统日志的过滤规则，将 plugins/ 从噪音黑名单中移除，这样插件目录的改动以后也能被正常记录。'
                    '正确示范3：scripts/soul_backup.py -> 修改了灵魂备份脚本，将跨网连接等待时间从10秒延长到12秒，减少 Win10 推送超时。'
                )
            },
            {
                'role': 'user',
                'content': json.dumps({'file': path, 'git_diff': content[:4200]}, ensure_ascii=False)
            }
        ],
        'temperature': 0.0,
    }
    try:
        url = MODEL_BASE.rstrip('/') + '/chat/completions'
        r = requests.post(url, headers={'Authorization': f'Bearer {MODEL_KEY}'}, json=prompt, timeout=90)
        r.raise_for_status()
        text = r.json()['choices'][0]['message']['content'].strip()
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'[A-Za-z_][A-Za-z0-9_./()=,\-]{6,}', '', text)
        return sanitize_summary(text, path, content)
    except Exception:
        return fallback_summary(path, content)


def collect_entries(rev: str, extra_notes=''):
    entries = []
    for rel in commit_files(rev):
        diff_text = commit_diff_for(rev, rel)
        human = summarize_change(rel, diff_text)
        entries.append({
            'time': commit_time_bjt(rev),
            'file': rel,
            'summary': human,
        })
    if extra_notes.strip():
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
        entries.append({
            'time': now.strftime('%Y-%m-%d %H:%M:%S BJT'),
            'file': '本次补充说明',
            'summary': extra_notes.strip(),
        })
    return entries


def build_log(extra_notes='', rev: str | None = None):
    rev = target_commit(rev)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    date_str = now.strftime('%Y-%m-%d')
    entries = collect_entries(rev, extra_notes)
    lines = [
        f'# 系统变更日志｜{date_str}',
        '',
        '## 今日变更摘要',
        '以下内容只聚焦最近一次核心提交的真实 Commit Diff，且已物理屏蔽 memory/、reports/、.log、.jsonl 等运行噪音：',
        '',
        f'- 目标提交：`{rev}`',
        f'- 提交说明：{commit_subject(rev)}',
        f'- 提交时间：{commit_time_bjt(rev)}',
        '',
    ]
    if not entries:
        lines.append('- [无核心变更] 本次提交未命中允许上墙的核心脚本或配置文件。')
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


def main(extra_notes='', rev: str | None = None):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    file = REPORTS / f'{now.strftime("%Y-%m-%d")}_update_log.md'
    file.parent.mkdir(parents=True, exist_ok=True)
    text = build_log(extra_notes, rev=rev)
    file.write_text(text, encoding='utf-8')
    remote_file, size = push_to_win10(file)
    github = sync_to_github(file)
    state = {
        'last_push_bjt': now.strftime('%Y-%m-%d %H:%M:%S'),
        'target_commit': target_commit(rev),
        'remote_file': remote_file,
        'size': size,
        'github': github,
    }
    (MEMORY / 'system_change_log_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    note = sys.argv[1] if len(sys.argv) > 1 else ''
    rev = sys.argv[2] if len(sys.argv) > 2 else None
    main(note, rev)
