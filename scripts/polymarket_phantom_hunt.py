#!/usr/bin/env python3
import json
import os
import subprocess
import time
from pathlib import Path

import paramiko
import requests

REPO = Path('/root/.openclaw/workspace/github_sync/laicai-007')
TARGET_FILES = [
    REPO / 'target_screenshot.png',
    REPO / 'phantom_status.txt',
    REPO / 'heavy_scraper_runtime.log',
]
WIN_STAGE = '/D:/来财/openclaw/polymarket_target_screenshot.png'
WIN_FINAL = 'D:/来财/幽灵战利品/polymarket_target_screenshot.png'
WIN_DIR = 'D:/来财/幽灵战利品'
CODESPACE_MACHINE = 'standardLinux32gb'


def sh(cmd, check=True):
    p = subprocess.run(cmd, cwd=str(REPO), text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f'cmd failed: {cmd}\nstdout={p.stdout}\nstderr={p.stderr}')
    return p


def log(msg):
    print(msg, flush=True)


def load_token():
    data = json.loads(Path('/root/openclaw/skills/minion_registry.json').read_text())
    return data['github_token']


def github_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }


def clean_local_artifacts():
    removed = []
    for path in TARGET_FILES:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    log('CLEAN_REMOVED ' + json.dumps(removed, ensure_ascii=False))
    return removed


def head_commit():
    return sh(['git', 'rev-parse', 'HEAD']).stdout.strip()


def latest_remote_auto_payload():
    sh(['git', 'fetch', 'origin', 'main'])
    out = sh(['git', 'log', 'origin/main', '--format=%H%x09%s', '-20']).stdout.strip().splitlines()
    for line in out:
        if '\t' not in line:
            continue
        commit, subject = line.split('\t', 1)
        if subject.startswith('Auto Payload:'):
            return {'commit': commit, 'subject': subject}
    return None


def create_codespace():
    p = subprocess.run(
        ['python3', '/root/openclaw/skills/phantom_node_summoner.py', 'create', 'main', '-', CODESPACE_MACHINE],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(p.stdout)
    return data['name']


def wait_codespace_available(name, headers):
    for i in range(120):
        r = requests.get(f'https://api.github.com/user/codespaces/{name}', headers=headers, timeout=60)
        r.raise_for_status()
        j = r.json()
        log(f"CODESPACE_POLL {i} {j.get('state')} {j.get('updated_at')}")
        if j.get('state') == 'Available':
            return
        time.sleep(5)
    raise RuntimeError('codespace not available in time')


def wait_for_new_payload(baseline_head, baseline_auto_commit):
    time.sleep(150)
    for i in range(80):
        log(f'PULL_ROUND {i}')
        sh(['git', 'fetch', 'origin', 'main'])
        auto = latest_remote_auto_payload()
        if auto:
            log('REMOTE_AUTO ' + json.dumps(auto, ensure_ascii=False))
        if auto and auto['commit'] != baseline_auto_commit:
            remote_changed = sh(['git', 'diff', '--name-only', f'{baseline_head}..origin/main', '--']).stdout.strip().splitlines()
            log('REMOTE_CHANGED ' + json.dumps(remote_changed, ensure_ascii=False))
            required = {'target_screenshot.png', 'phantom_status.txt'}
            if required.issubset(set(remote_changed)):
                sh(['git', 'pull', '--rebase', 'origin', 'main'])
                local_head = head_commit()
                if local_head == auto['commit'] and (REPO / 'target_screenshot.png').exists() and (REPO / 'target_screenshot.png').stat().st_size > 0:
                    size = (REPO / 'target_screenshot.png').stat().st_size
                    log(f'VALID_SCREENSHOT_LANDED {size}')
                    return {'commit': auto['commit'], 'subject': auto['subject'], 'size': size}
        time.sleep(15)
    raise RuntimeError('timed out waiting for fresh Auto Payload commit and artifact')


def delete_codespace(name, headers):
    r = requests.delete(f'https://api.github.com/user/codespaces/{name}', headers=headers, timeout=60)
    log(f'DELETE_STATUS {r.status_code}')
    r.raise_for_status()


def verify_zero_codespaces():
    p = subprocess.run(
        ['python3', '/root/openclaw/skills/phantom_node_summoner.py', 'list'],
        text=True,
        capture_output=True,
        check=True,
    )
    log('FINAL_CODESPACES ' + p.stdout.strip())
    return json.loads(p.stdout)


def push_to_win10():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('100.89.160.67', username='Administrator', password='As1231', timeout=20)
    sftp = ssh.open_sftp()
    sftp.put(str(REPO / 'target_screenshot.png'), WIN_STAGE)
    sftp.close()
    ps = (
        f"New-Item -ItemType Directory -Force -Path '{WIN_DIR}' | Out-Null; "
        f"Move-Item -Force 'D:/来财/openclaw/polymarket_target_screenshot.png' '{WIN_FINAL}'; "
        f"Get-Item '{WIN_FINAL}' | Select-Object FullName,Length,LastWriteTime | Format-List"
    )
    stdin, stdout, stderr = ssh.exec_command(f'powershell -NoProfile -Command "{ps}"')
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    ssh.close()
    log('WIN10_RECEIPT_START')
    log(out)
    log('WIN10_RECEIPT_END')
    if err:
        log('WIN10_ERR ' + err)
    return out, err


def main():
    token = load_token()
    headers = github_headers(token)

    baseline_head = head_commit()
    baseline_auto = latest_remote_auto_payload()
    baseline_auto_commit = baseline_auto['commit'] if baseline_auto else None
    log('BASELINE_HEAD ' + baseline_head)
    log('BASELINE_AUTO ' + json.dumps(baseline_auto, ensure_ascii=False))

    clean_local_artifacts()

    name = create_codespace()
    log('CODESPACE_NAME ' + name)

    try:
        wait_codespace_available(name, headers)
        result = wait_for_new_payload(baseline_head, baseline_auto_commit)
        delete_codespace(name, headers)
        zero = verify_zero_codespaces()
        receipt, err = push_to_win10()
        print(json.dumps({
            'cleaned': True,
            'codespace': name,
            'artifact': result,
            'win10_receipt': receipt,
            'win10_err': err,
            'final_codespaces': zero,
        }, ensure_ascii=False))
    except Exception:
        try:
            delete_codespace(name, headers)
        except Exception as e:
            log('DELETE_FAIL ' + repr(e))
        try:
            verify_zero_codespaces()
        except Exception as e:
            log('FINAL_CODESPACE_CHECK_FAIL ' + repr(e))
        raise


if __name__ == '__main__':
    main()
