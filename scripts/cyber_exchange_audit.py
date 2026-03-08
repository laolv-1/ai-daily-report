#!/usr/bin/env python3
import datetime as dt
import json
import sys
import time
from pathlib import Path

import paramiko
import requests

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports' / 'cyber-exchange'
REPORT_DIR.mkdir(parents=True, exist_ok=True)
APPROVAL_OUTBOX_DIR = ROOT / 'reports' / 'approval-outbox'
APPROVAL_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = ROOT / 'memory' / 'moltbook_approval_state.json'
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
RUN_LOG = ROOT / 'reports' / 'cyber-exchange-last-run.log'
OPENCLAW_CONFIG = Path('/root/.openclaw/openclaw.json')

ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_DRAFT_DIR = '/www/wwwroot/spider_center/molt_learning/'
CHAT_ID = '7392107275'
HIGH_VALUE_SCORE = 12
ALLOWED_BJT_HOURS = {0, 12}


def load_laicai_bot_token() -> str:
    obj = json.loads(OPENCLAW_CONFIG.read_text(encoding='utf-8'))
    return obj['channels']['telegram']['botToken']


def log_line(text: str) -> None:
    stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with RUN_LOG.open('a', encoding='utf-8') as f:
        f.write(f'[{stamp}] {text}\n')


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {'processed_remote_files': []}
    try:
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {'processed_remote_files': []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def connect_sftp():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(
        hostname=ALIYUN_HOST,
        username=ALIYUN_USER,
        password=ALIYUN_PASSWORD,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
    )
    return cli, cli.open_sftp()


def list_remote_drafts():
    cli, sftp = connect_sftp()
    try:
        entries = []
        for attr in sftp.listdir_attr(ALIYUN_DRAFT_DIR):
            name = attr.filename
            if not name.endswith('.draft'):
                continue
            entries.append({
                'name': name,
                'remote_path': ALIYUN_DRAFT_DIR + name,
                'mtime': int(getattr(attr, 'st_mtime', 0) or 0),
                'size': int(getattr(attr, 'st_size', 0) or 0),
            })
        entries.sort(key=lambda x: (x['mtime'], x['name']), reverse=True)
        return entries
    finally:
        sftp.close()
        cli.close()


def read_remote_text(remote_path: str) -> str:
    cli, sftp = connect_sftp()
    try:
        with sftp.open(remote_path, 'r') as f:
            raw = f.read()
        if isinstance(raw, bytes):
            return raw.decode('utf-8', 'ignore')
        return str(raw)
    finally:
        sftp.close()
        cli.close()


def normalize_payload(remote_file: dict, text: str) -> dict:
    text = (text or '').strip()
    payload = {}
    try:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            payload = {'raw_text': text}
    except Exception:
        payload = {'raw_text': text}

    logic_name = payload.get('logic_name') or payload.get('title') or remote_file['name']
    summary = payload.get('summary') or payload.get('content') or payload.get('raw_text') or ''
    labels = payload.get('labels') or []
    if isinstance(labels, str):
        labels = [labels]
    score = int(payload.get('score') or 0)
    if score <= 0:
        score = min(20, max(6, len(summary) // 160 + len(labels) * 2))
    source_url = payload.get('source_url') or payload.get('url') or ''

    return {
        'logic_name': str(logic_name).strip(),
        'summary': str(summary).strip(),
        'labels': [str(x).strip() for x in labels if str(x).strip()],
        'score': score,
        'source_url': str(source_url).strip(),
        'remote_path': remote_file['remote_path'],
        'remote_name': remote_file['name'],
        'mtime': remote_file['mtime'],
        'size': remote_file['size'],
    }


def pick_new_high_value_draft():
    state = load_state()
    processed = set(state.get('processed_remote_files', []))
    remote_files = list_remote_drafts()
    for remote_file in remote_files:
        if remote_file['name'] in processed:
            continue
        text = read_remote_text(remote_file['remote_path'])
        payload = normalize_payload(remote_file, text)
        state.setdefault('processed_remote_files', []).append(remote_file['name'])
        state['processed_remote_files'] = state['processed_remote_files'][-200:]
        save_state(state)
        if payload['score'] < HIGH_VALUE_SCORE:
            log_line(f'SKIP_LOW_VALUE file={remote_file["name"]} score={payload["score"]}')
            continue
        return payload
    log_line('SILENT_EXIT no_new_high_value_remote_draft')
    return None


def build_approval_request(item: dict) -> str:
    ts = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    labels = ' / '.join(item['labels']) if item['labels'] else '未标注'
    summary = item['summary'][:900] if item['summary'] else '（草稿摘要为空）'
    lines = [
        '【来财·MolTBook 审批单】',
        f'时间：{ts}',
        '',
        f'逻辑名称：{item["logic_name"]}',
        f'命中标签：{labels}',
        f'信号评分：{item["score"]}',
        '',
        '【提纯摘要】',
        summary,
        '',
        '【隔离回执】',
        f'- 阿里云取件路径：{item["remote_path"]}',
        f'- 远端文件名：{item["remote_name"]}',
    ]
    if item['source_url']:
        lines.append(f'- 原帖链接：{item["source_url"]}')
    lines.extend([
        '',
        '【主公请审批：回复“采纳”或“舍弃”】',
    ])
    return '\n'.join(lines)


def write_approval_outbox(text: str, remote_name: str) -> Path:
    out = APPROVAL_OUTBOX_DIR / f'approval-request-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}-{remote_name}.md'
    out.write_text(text, encoding='utf-8')
    return out


def enforce_bjt_delivery_window() -> None:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    if now.minute == 0 and now.hour in ALLOWED_BJT_HOURS:
        return
    log_line(f'SILENT_EXIT outside_bjt_window now={now.strftime("%Y-%m-%d %H:%M:%S %Z") or "BJT"}')
    raise SystemExit(0)


def send_report(text: str):
    enforce_bjt_delivery_window()
    bot_token = load_laicai_bot_token()
    payload = {
        'chat_id': CHAT_ID,
        'text': text[:3500],
        'disable_web_page_preview': True,
    }
    r = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(r.text)
    return data


def main():
    try:
        item = pick_new_high_value_draft()
        if not item:
            raise SystemExit(0)
        enforce_bjt_delivery_window()
        approval_request = build_approval_request(item)
        approval_out = write_approval_outbox(approval_request, item['remote_name'])
        send_result = send_report(approval_request)
        log_line(f'TELEGRAM_OK remote={item["remote_name"]} message_id={send_result["result"]["message_id"]}')
        print(str(approval_out))
        print(json.dumps({
            'remote_path': item['remote_path'],
            'score': item['score'],
            'message_id': send_result['result']['message_id'],
        }, ensure_ascii=False))
    except SystemExit:
        raise
    except Exception as e:
        log_line(f'ERROR {type(e).__name__}: {e}')
        raise


if __name__ == '__main__':
    main()
