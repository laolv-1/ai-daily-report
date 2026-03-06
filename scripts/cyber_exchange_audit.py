#!/usr/bin/env python3
import datetime as dt
import json
import os
from pathlib import Path

import paramiko
import requests

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports' / 'cyber-exchange'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = 'https://api.moltbook.io/v1/streams/general-logic'
API_TOKEN = 'MB-RO-LC-9981-ALFA'
TOPICS = ['automation', 'agent-safety', 'observability', 'sandboxing', 'prompt-defense']

ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_DRAFT_DIR = '/www/wwwroot/spider_center/molt_learning/'

BOT_TOKEN = '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0'
CHAT_ID = '7392107275'

SAFE_REWRITE_RULE = '只保留机制逻辑、架构思想、伪代码建议；不保存、不执行外部原始代码。'


def fetch_topic(topic):
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Accept': 'application/json',
        'User-Agent': 'OpenClaw-CyberExchange/1.0',
    }
    r = requests.get(API_URL, headers=headers, params={'topic': topic}, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data if isinstance(data, list) else data.get('items', [])
    cleaned = []
    for item in items[:10]:
        text = json.dumps(item, ensure_ascii=False)
        cleaned.append({
            'topic': topic,
            'logic_name': item.get('title') or item.get('name') or f'{topic}-logic',
            'summary': (item.get('summary') or item.get('content') or text)[:800],
            'rewrite_hint': '以纯净本地代码重写为只读采集、隔离存放、最小权限执行模块。'
        })
    return cleaned


def save_draft_to_aliyun(name, payload):
    ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    local = REPORT_DIR / f'{ts}-{name}.draft'
    local.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=ALIYUN_HOST, username=ALIYUN_USER, password=ALIYUN_PASSWORD, timeout=10, banner_timeout=10, auth_timeout=10)
    sftp = cli.open_sftp()
    remote = ALIYUN_DRAFT_DIR + local.name
    sftp.put(str(local), remote)
    sftp.close()
    cli.close()
    return local.name, remote


def send_report(text):
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': CHAT_ID, 'text': text[:3500], 'disable_web_page_preview': True},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    ts = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    results = []
    errors = []
    for topic in TOPICS:
        try:
            items = fetch_topic(topic)
            for item in items[:2]:
                fname, remote = save_draft_to_aliyun(topic, item)
                results.append((topic, item['logic_name'], fname, remote))
        except Exception as e:
            errors.append((topic, f'{type(e).__name__}: {e}'))
    lines = [f'🧠 赛博交流战报', f'时间：{ts}', '', '【交流获取的新逻辑】']
    if results:
        for topic, logic_name, fname, remote in results[:8]:
            lines.append(f'- {topic}｜{logic_name}｜草稿: {fname}')
    else:
        lines.append('- 本轮未抓到新逻辑，已保留探测状态。')
    lines.append('')
    lines.append('【系统增益评估】')
    lines.append('- 强化自动化可观测性、隔离执行、提示防御与审计链路。')
    lines.append('')
    lines.append('【代码级重写建议】')
    lines.append('- 仅保留伪代码与架构建议，正式技能必须由本地纯净重写。')
    lines.append('')
    lines.append('【等待主公审批】')
    lines.append('- TG 回复：采纳 [逻辑名] / 舍弃 [逻辑名]')
    if errors:
        lines.append('')
        lines.append('【异常回执】')
        for topic, err in errors[:5]:
            lines.append(f'- {topic}｜{err}')
    report = '\n'.join(lines)
    out = REPORT_DIR / f'cyber-exchange-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    out.write_text(report, encoding='utf-8')
    send_report(report)
    print(out)
    print(report)


if __name__ == '__main__':
    main()
