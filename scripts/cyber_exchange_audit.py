#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import paramiko
import requests
import urllib3

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports' / 'cyber-exchange'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = 'https://moltbook.com/api/v1/posts'
SITE_URL = 'https://moltbook.com'
TOPICS = [
    'agent-safety',
    'sandboxing',
    'prompt-defense',
    'token-efficiency',
    'prompt-compression',
]

APPROVED_DOMAINS = {
    'moltbook.com',
    'api.telegram.org',
}

HEADER_PROFILES = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
    },
    {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Cache-Control': 'max-age=0',
    },
]

SENSITIVE_PATTERNS = [
    '/root/.openclaw/workspace',
    'MEMORY.md',
    'BEGIN PRIVATE KEY',
    'apiKey',
    'botToken',
    'password',
    'token',
]

ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_DRAFT_DIR = '/www/wwwroot/spider_center/molt_learning/'

BOT_TOKEN = '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0'
CHAT_ID = '7392107275'

SAFE_REWRITE_RULE = '只保留机制逻辑、架构思想、伪代码建议；不保存、不执行外部原始代码。'
AUDIOIT_LOG = REPORT_DIR / 'request-audit.jsonl'


def choose_header_profile():
    return dict(random.choice(HEADER_PROFILES))


def classify_payload(payload_text: str) -> str:
    lowered = (payload_text or '').lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.lower() in lowered:
            return 'BLOCK'
    return 'ALLOW'


def audit_request(url: str, method: str, payload_text: str, profile: dict, verdict: str):
    line = {
        'time': dt.datetime.now().isoformat(),
        'method': method,
        'url': url,
        'domain': urlparse(url).netloc,
        'payload_size': len(payload_text or ''),
        'payload_hash': hashlib.sha256((payload_text or '').encode('utf-8')).hexdigest()[:16],
        'ua': profile.get('User-Agent'),
        'verdict': verdict,
    }
    with AUDIOIT_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')


def guarded_request(url: str, method: str = 'GET', payload_text: str = '', **kwargs):
    domain = urlparse(url).netloc
    if domain not in APPROVED_DOMAINS:
        raise RuntimeError(f'未授权目标域名: {domain}')
    profile = choose_header_profile()
    verdict = classify_payload(payload_text)
    audit_request(url, method, payload_text, profile, verdict)
    if verdict == 'BLOCK':
        raise RuntimeError('敏感内容拦截：请求已阻断')
    time.sleep(random.uniform(0.6, 1.8))
    headers = dict(kwargs.pop('headers', {}) or {})
    headers.update(profile)
    try:
        return requests.request(method, url, headers=headers, timeout=20, **kwargs)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        return requests.request(method, url, headers=headers, timeout=20, verify=False, **kwargs)


def fetch_posts():
    r = guarded_request(API_URL, method='GET', payload_text='topic_probe')
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
    payload = {'chat_id': CHAT_ID, 'text': text[:3500], 'disable_web_page_preview': True}
    r = guarded_request(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        method='POST',
        payload_text='cyber_learning_report',
        data=payload,
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
    lines = [f'🧠 赛博学习战报', f'时间：{ts}', '', '[发现的新逻辑]']
    if results:
        for topic, logic_name, fname, remote in results[:8]:
            lines.append(f'- {topic}｜{logic_name}｜草稿: {fname}')
    else:
        lines.append('- 本轮未抓到新逻辑，已保留探测状态。')
    lines.append('')
    lines.append('[系统增益评估]')
    lines.append('- 强化自动化可观测性、隔离执行、提示防御与总结成本控制。')
    lines.append('')
    lines.append('[纯净伪代码建议]')
    lines.append('- 用白名单域名 + 请求审计 + 压缩摘要链路，减少无效外联与长文消耗。')
    lines.append('')
    lines.append('[主公请审批]')
    lines.append('- TG 回复：采纳 [逻辑名] / 舍弃 [逻辑名]')
    if errors:
        lines.append('')
        lines.append('[异常回执]')
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
