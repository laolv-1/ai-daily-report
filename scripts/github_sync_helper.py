#!/usr/bin/env python3
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace')
SYNC_ROOT = ROOT / 'github_sync' / 'laicai-007'
REGISTRY = Path('/root/openclaw/skills/minion_registry.json')
GIT_REMOTE = 'https://github.com/laolv-1/laicai-007.git'
GIT_USER_NAME = '来财'
GIT_USER_EMAIL = 'laicai-007@users.noreply.github.com'


def load_token() -> str:
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    token = data.get('github_token', '').strip()
    if not token:
        raise RuntimeError('minion_registry.json 缺少 github_token')
    return token


def authed_remote() -> str:
    token = load_token()
    return f'https://oauth2:{token}@github.com/laolv-1/laicai-007.git'


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError((p.stdout or '') + '\n' + (p.stderr or ''))
    return (p.stdout or '').strip()


def ensure_repo() -> Path:
    repo = SYNC_ROOT
    repo.parent.mkdir(parents=True, exist_ok=True)
    if not repo.exists():
        run(['git', 'clone', authed_remote(), str(repo)])
    run(['git', 'config', 'user.name', GIT_USER_NAME], cwd=repo)
    run(['git', 'config', 'user.email', GIT_USER_EMAIL], cwd=repo)
    run(['git', 'remote', 'set-url', 'origin', authed_remote()], cwd=repo)
    return repo


def copy_into_repo(source: Path, dest_rel: str) -> Path:
    repo = ensure_repo()
    dst = repo / dest_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dst)
    return dst


def write_text_into_repo(text: str, dest_rel: str) -> Path:
    repo = ensure_repo()
    dst = repo / dest_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding='utf-8')
    return dst


def commit_and_push(message: str) -> dict:
    repo = ensure_repo()
    run(['git', 'add', '.'], cwd=repo)
    status = run(['git', 'status', '--porcelain'], cwd=repo)
    if not status:
        head = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo)
        return {'changed': False, 'commit': head}
    run(['git', 'commit', '-m', message], cwd=repo)
    run(['git', 'push', 'origin', 'HEAD'], cwd=repo)
    head = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo)
    return {'changed': True, 'commit': head}


def dated_rel_path(prefix: str, filename: str) -> str:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    return f'{prefix}/{now.strftime("%Y-%m-%d")}/{filename}'
