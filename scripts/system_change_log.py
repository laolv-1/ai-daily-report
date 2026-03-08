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
MODEL_NAME = 'lck/gpt-5.4'
MAX_FILES = 8
MAX_DIFF_CHARS = 6000
BLACKLIST_PHRASES = [
    '更新了逻辑', '修改了逻辑', '优化了代码', '修改了配置', '更改了状态',
    '更新了文档', '更新了说明文字', '调整了逻辑', '做了优化', '做了调整',
    '更新了该文件的逻辑或运行状态', '更新了状态记录或结构化配置',
    '本次变更涉及', '关键标记', '运行状态变化'
]
CORE_ROOT_FILES = {'.gitignore', '.env', 'package.json', 'pnpm-lock.yaml'}
CORE_SUFFIXES = ('.py', '.sh', '.json', '.md')
NOISE_PREFIXES = ('memory/', 'reports/', 'github_sync/', '.openclaw/', 'tmp_', 'memory-lancedb-pro/', 'plugins/')
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


def tracked_changes():
    names = []
    for cmd in (
        ['git', 'diff', '--name-only'],
        ['git', 'diff', '--cached', '--name-only'],
        ['git', 'ls-files', '--others', '--exclude-standard'],
    ):
        out = run(cmd, check=False)
        for line in out.splitlines():
            line = line.strip()
            if line and line not in names and is_allowed_path(line):
                names.append(line)
    names.sort(key=lambda p: (0 if p.startswith('scripts/') else 1, p))
    return names[:MAX_FILES]


def file_mtime(path: Path) -> str:
    if not path.exists():
        return '未落盘'
    ts = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone(dt.timedelta(hours=8)))
    return ts.strftime('%Y-%m-%d %H:%M:%S BJT')


def is_untracked(path: str) -> bool:
    out = run(['git', 'ls-files', '--others', '--exclude-standard', '--', path], check=False)
    return bool(out.strip())


def diff_for(path: str) -> str:
    try:
        if is_untracked(path):
            p = ROOT / path
            if p.exists():
                text = p.read_text(encoding='utf-8', errors='ignore')
                return f'UNTRACKED_FILE\n{text[:MAX_DIFF_CHARS]}'
        diff = run(['git', 'diff', '--', path], check=False)
        cached = run(['git', 'diff', '--cached', '--', path], check=False)
        merged = '\n'.join(part for part in [cached, diff] if part.strip()).strip()
        if merged:
            return merged[:MAX_DIFF_CHARS]
        p = ROOT / path
        if p.exists():
            return f'FILE_CONTENT\n{p.read_text(encoding="utf-8", errors="ignore")[:MAX_DIFF_CHARS]}'
        return f'文件不存在：{path}'
    except Exception as e:
        return f'无法读取差异：{path} | {e}'


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
    for old in removed[:20]:
        for new in added[:20]:
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
            if line in ('{', '}', '[', ']', '(', ')'):
                continue
            out.append(line)
        if len(out) >= limit:
            break
    return out


def fallback_summary(path: str, content: str) -> str:
    pairs = extract_value_changes(content)
    if pairs:
        key, old, new = pairs[0]
        return f'将 {key} 从 {old} 改为 {new}。'
    lines = meaningful_lines(content, limit=3)
    if lines:
        core = lines[0]
        if len(core) > 140:
            core = core[:137] + '...'
        return f'新增或修改核心代码行：{core}'
    return '该文件有变更，但当前只抓到很少的有效差异。'


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
                    '你是一个冷酷的战术分析师。你只能根据真实 git diff 输出一句中文结论。'
                    '只允许写具体变量名、函数名、参数数值、超时时间、文件路径或新增代码行。'
                    '严禁输出：更新了逻辑、修改了配置、优化了代码、更改了状态、本次变更涉及、关键标记。'
                    '如果不确定，就直接提取 diff 中最关键的新增代码行或数值变化，绝不允许发明宽泛总结词。'
                    'Few-shot 示例1：scripts/market_research_daily.py -> 将 requests.get 的 timeout 参数从 20 改为 25。'
                    'Few-shot 示例2：scripts/soul_backup.py -> 将 banner_timeout、auth_timeout 和 timeout 的等待时间从 10 延长至 12。'
                    'Few-shot 示例3：scripts/system_change_log.py -> 新增 BLACKLIST_PHRASES，并在 sanitize_summary 中拦截“本次变更涉及”这类废话。'
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
        return sanitize_summary(text, path, content)
    except Exception:
        return fallback_summary(path, content)


def collect_entries(extra_notes=''):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    entries = []
    for rel in tracked_changes():
        p = ROOT / rel
        diff_text = diff_for(rel)
        human = summarize_change(rel, diff_text)
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
        '以下内容只聚焦核心脚本与配置变更，已物理屏蔽 memory/、reports/、.log、.jsonl 等运行噪音：',
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
