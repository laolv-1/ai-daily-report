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
MAX_FILES = 10
MAX_DIFF_CHARS = 6000
BLACKLIST_PHRASES = [
    '更新了逻辑', '修改了逻辑', '优化了代码', '修改了配置', '更改了状态',
    '更新了文档', '更新了说明文字', '调整了逻辑', '做了优化', '做了调整',
    '更新了该文件的逻辑或运行状态', '更新了状态记录或结构化配置'
]


def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError((p.stdout or '') + '\n' + (p.stderr or ''))
    return (p.stdout or '').strip()


def _score_path(path: str) -> tuple:
    score = 100
    if path.startswith('scripts/'):
        score -= 50
    if path.endswith(('.py', '.sh', '.md', '.json')):
        score -= 20
    if path == '.gitignore':
        score -= 30
    if path.startswith('memory/'):
        score += 30
    if path.startswith('reports/'):
        score += 20
    if path.endswith(('.log', '.jsonl')):
        score += 40
    return (score, path)


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
            if line and line not in names:
                names.append(line)
    names.sort(key=_score_path)
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
        if path.startswith('/root/'):
            p = Path(path)
            if not p.exists():
                return f'文件不存在：{path}'
            text = p.read_text(encoding='utf-8', errors='ignore')
            return f'FILE_CONTENT\n{text[:MAX_DIFF_CHARS]}'
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


def extract_tokens(diff_text: str, limit: int = 6):
    tokens = []
    seen = set()
    patterns = [
        r'[A-Za-z_][A-Za-z0-9_]{2,}',
        r'\b\d+(?:\.\d+)?\b',
        r"'[^'\n]{2,80}'",
        r'"[^"\n]{2,80}"',
    ]
    for pat in patterns:
        for m in re.findall(pat, diff_text):
            tok = str(m).strip()
            if tok in seen:
                continue
            if tok.lower() in {'true', 'false', 'none', 'json', 'utf', 'ignore'}:
                continue
            seen.add(tok)
            tokens.append(tok)
            if len(tokens) >= limit:
                return tokens
    return tokens


def fallback_summary(path: str, content: str) -> str:
    lines = meaningful_lines(content, limit=4)
    tokens = extract_tokens(content, limit=6)
    if lines:
        quoted = '；'.join(lines[:2])
        if len(quoted) > 160:
            quoted = quoted[:157] + '...'
        return f'关键改动直接体现在代码差异：{quoted}'
    if tokens:
        return f'本次变更涉及关键标记：{", ".join(tokens[:6])}'
    p = ROOT / path
    if p.exists():
        head = p.read_text(encoding='utf-8', errors='ignore')[:160].replace('\n', ' ')
        return f'该文件当前开头内容为：{head}'
    return '该文件有变更，但当前未能提取出可读差异片段。'


def sanitize_summary(text: str, path: str, content: str) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip(' -：:')
    if not text:
        return fallback_summary(path, content)
    for bad in BLACKLIST_PHRASES:
        if bad in text:
            return fallback_summary(path, content)
    if len(text) < 10:
        return fallback_summary(path, content)
    return text


def summarize_change(path: str, content: str) -> str:
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是系统变更审计官。你必须把 git diff 翻译成一句可复盘的中文战术简报。'
                    '你只能根据我给你的真实差异内容作答，必须点出具体函数名、变量名、参数值、阈值、超时时间、文件路径、提交文案或核心文案变化。'
                    '严禁使用以下废话：更新了逻辑、修改了配置、优化了代码、更改了状态、更新了文档、做了调整、运行状态变化。'
                    '如果 diff 里出现数值变化，必须写出“从多少改到多少”。'
                    '如果 diff 里出现函数名、变量名、字段名、文件路径，必须至少点名 1-2 个。'
                    '输出只允许一句中文，不要前言，不要解释过程，不要模糊词，不要套话。'
                    '示例：将 MAX_FILES 从 12 改为 10，并新增 BLACKLIST_PHRASES 黑名单来拦截“更新了逻辑”这类废话。'
                )
            },
            {
                'role': 'user',
                'content': json.dumps({'file': path, 'git_diff': content[:4200]}, ensure_ascii=False)
            }
        ],
        'temperature': 0.1,
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
        '以下内容已基于真实 git diff 生成，目标是让主公能直接复盘具体动作：',
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
