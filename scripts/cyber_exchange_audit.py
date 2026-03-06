#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path

import paramiko
import requests
import urllib3

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports' / 'cyber-exchange'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = 'https://moltbook.com/api/v1/posts'
SITE_URL = 'https://moltbook.com'
TOPICS = ['automation', 'agent-safety', 'observability', 'sandboxing', 'prompt-defense']
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
}

ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_DRAFT_DIR = '/www/wwwroot/spider_center/molt_learning/'

BOT_TOKEN = '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0'
CHAT_ID = '7392107275'

SAFE_REWRITE_RULE = '只保留机制逻辑、架构思想、伪代码建议；不保存、不执行外部原始代码。'


def safe_get(url, **kwargs):
    try:
        return requests.get(url, timeout=20, **kwargs)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        kwargs['verify'] = False
        return requests.get(url, timeout=20, **kwargs)


def fetch_posts():
    r = safe_get(API_URL, headers=BROWSER_HEADERS)
    r.raise_for_status()
    data = r.json()
    return data.get('posts', []) if isinstance(data, dict) else data


def fetch_topic(topic):
    posts = fetch_posts()
    cleaned = []
    for item in posts[:80]:
        title = item.get('title', '')
        content = item.get('content', '')
        hay = f"{title}\n{content}".lower()
        if topic.lower() not in hay:
            continue
        if any(bad in hay for bad in ['exploit chain', 'bypass detection', 'evade ban', 'steal token', 'payload dropper']):
            continue
        cleaned.append({
            'topic': topic,
            'logic_name': title or item.get('id') or f'{topic}-logic',
            'summary': content[:800],
            'source_url': f"{SITE_URL}/posts/{item.get('id')}" if item.get('id') else SITE_URL,
            'rewrite_hint': '以纯净本地代码重写为只读采集、隔离存放、最小权限执行模块。',
            'safety_rule': SAFE_REWRITE_RULE,
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
    lines = [f'🧠 赛博学习战报', f'时间：{ts}', '', '【发现的新逻辑】']
    if results:
        for topic, logic_name, fname, remote in results[:8]:
            lines.append(f'- {topic}｜{logic_name}｜草稿: {fname}')
    else:
        lines.append('- 本轮未抓到新逻辑，已保留探测状态。')
    lines.append('')
    lines.append('【系统增益评估】')
    lines.append('- 强化自动化可观测性、隔离执行、提示防御与审计链路。')
    lines.append('')
    lines.append('【主公是否采纳的请示】')
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
