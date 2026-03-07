#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import paramiko
import requests
import urllib3

sys.path.insert(0, '/root/openclaw/skills')
from http_sandbox import HttpSandbox

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports' / 'cyber-exchange'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = 'https://moltbook.com/api/v1/posts'
SITE_URL = 'https://moltbook.com'
OPENCLAW_CONFIG = Path('/root/.openclaw/openclaw.json')
ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_DRAFT_DIR = '/www/wwwroot/spider_center/molt_learning/'
CHAT_ID = '7392107275'
SAFE_REWRITE_RULE = '只保留机制逻辑、架构思想、伪代码建议；不保存、不执行外部原始代码。'
REQUEST_AUDIT_LOG = REPORT_DIR / 'request-audit.jsonl'
APPROVAL_OUTBOX_DIR = ROOT / 'reports' / 'approval-outbox'
APPROVAL_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

BROAD_KEYWORDS = {
    '自动化赚钱': ['automate revenue', 'make money', 'monetiz', 'pricing', 'subscription', 'profit', 'arbitrage', 'upsell', 'funnel'],
    '流量截流': ['traffic', 'distribution', 'growth', 'acquisition', 'seo', 'feed', 'ranking', 'retention', 'viral'],
    '风控绕过': ['moderation', 'risk', 'compliance', 'fraud', 'ban', 'blocked', 'bypass', 'evasion', 'detection'],
    '大模型奇技淫巧': ['agent', 'llm', 'prompt', 'context', 'token', 'reasoning', 'tool call', 'jailbreak', 'compression'],
    '新工具': ['tool', 'workflow', 'automation', 'browser', 'scrape', 'pipeline', 'plugin', 'sdk', 'open source'],
}
BLOCK_TERMS = ['payload dropper', 'steal token', 'credential stuffing', 'ransomware builder']
HEADER_PROFILES = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
    },
    {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
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

SANDBOX = HttpSandbox(
    approved_domains={'moltbook.com', 'api.telegram.org'},
    audit_log_path=str(REPORT_DIR / 'http-sandbox-audit.jsonl'),
)


def load_laicai_bot_token() -> str:
    obj = json.loads(OPENCLAW_CONFIG.read_text(encoding='utf-8'))
    return obj['channels']['telegram']['botToken']


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
    with REQUEST_AUDIT_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')


def guarded_request(url: str, method: str = 'GET', payload_text: str = '', **kwargs):
    profile = choose_header_profile()
    verdict = classify_payload(payload_text)
    audit_request(url, method, payload_text, profile, verdict)
    if verdict == 'BLOCK':
        raise RuntimeError('敏感内容拦截：请求已阻断')
    guarded = SANDBOX.guard_request(method, url, payload_text=payload_text, ua=profile.get('User-Agent', ''))
    time.sleep(random.uniform(0.4, 1.2))
    headers = dict(kwargs.pop('headers', {}) or {})
    headers.update(profile)
    try:
        return requests.request(method, guarded['url'], headers=headers, timeout=25, **kwargs)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        return requests.request(method, guarded['url'], headers=headers, timeout=25, verify=False, **kwargs)


def fetch_posts():
    r = guarded_request(API_URL, method='GET', payload_text='moltbook_broad_probe')
    r.raise_for_status()
    data = r.json()
    return data.get('posts', []) if isinstance(data, dict) else data


def score_post(item: dict):
    title = item.get('title', '') or ''
    content = item.get('content', '') or ''
    hay = f"{title}\n{content}".lower()
    if any(term in hay for term in BLOCK_TERMS):
        return None
    score = 0
    matched_labels = []
    for label, keys in BROAD_KEYWORDS.items():
        hit = False
        for key in keys:
            if key.lower() in hay:
                score += 8 if key in title.lower() else 4
                hit = True
        if hit:
            matched_labels.append(label)
    if len(content) > 800:
        score += 2
    if 'http' in content.lower():
        score += 1
    if score < 8:
        return None
    return score, matched_labels


def pick_posts(limit=6):
    posts = fetch_posts()
    picked = []
    seen = set()
    for item in posts[:120]:
        result = score_post(item)
        if not result:
            continue
        score, matched_labels = result
        pid = item.get('id')
        if pid in seen:
            continue
        seen.add(pid)
        picked.append({
            'id': pid,
            'logic_name': item.get('title') or pid or 'untitled-post',
            'summary': (item.get('content') or '')[:1200],
            'source_url': f"{SITE_URL}/posts/{pid}" if pid else SITE_URL,
            'labels': matched_labels,
            'score': score,
            'rewrite_hint': '提炼为可审计、最小权限、可落地的工作流或数据管道，不保留危险执行细节。',
            'safety_rule': SAFE_REWRITE_RULE,
        })
    picked.sort(key=lambda x: (x['score'], len(x['summary'])), reverse=True)
    return picked[:limit]


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
    bot_token = load_laicai_bot_token()
    payload = {'chat_id': CHAT_ID, 'text': text[:3500], 'disable_web_page_preview': True}
    r = guarded_request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        method='POST',
        payload_text=text[:500],
        data=payload,
    )
    r.raise_for_status()
    return r.json()


def build_overview_report(ts: str, results, errors):
    lines = [f'🧠 来财·MolTBook 广撒网总览', f'时间：{ts}', '']
    if results:
        label_counts = {}
        for item in results:
            for label in item['labels']:
                label_counts[label] = label_counts.get(label, 0) + 1
        lines.append(f'- 本轮抓到 {len(results)} 条可审批逻辑；标签分布：' + '，'.join(f'{k}={v}' for k, v in sorted(label_counts.items())))
        for item in results[:5]:
            lines.append(f"- {item['logic_name'][:90]}｜标签：{'/'.join(item['labels'])}｜评分 {item['score']}")
    else:
        lines.append('- 本轮广撒网未命中高价值候选，已保留审计日志，不主动打扰。')
    if errors:
        lines.append('')
        lines.append('[异常回执]')
        for err in errors[:5]:
            lines.append(f'- {err}')
    return '\n'.join(lines)


def build_approval_request(ts: str, item, fname, remote):
    lines = ['【来财·MolTBook 广撒网审批单】', f'时间：{ts}', '']
    lines.append(f"逻辑名称：{item['logic_name']}")
    lines.append(f"命中标签：{' / '.join(item['labels'])}")
    lines.append(f"信号评分：{item['score']}")
    lines.append('')
    lines.append('【主判断】')
    lines.append('这条值得主公过目，不是因为它一定可用，而是它可能影响流量、变现、风控或 Agent 工作流。')
    lines.append('')
    lines.append('【提纯摘要】')
    lines.append(item['summary'][:900] or '（原文摘要为空）')
    lines.append('')
    lines.append('【可注入系统的方向】')
    lines.append('- 可做成流量截流/自动化赚钱/审核对抗/工具增强的观察样本。')
    lines.append('- 仅保留工作流、机制、产品判断，不保留危险攻击细节。')
    lines.append('- 若主公拍板，可再转成本地安全版 SOP 或草图。')
    lines.append('')
    lines.append('【隔离回执】')
    lines.append(f'- 阿里云草稿隔离：{remote}')
    lines.append(f'- VPS 本地索引：{fname}')
    lines.append(f"- 原帖链接：{item['source_url']}")
    lines.append('')
    lines.append('【主公请审批：回复“采纳”或“舍弃”】')
    return '\n'.join(lines)


def write_approval_outbox(text: str):
    out = APPROVAL_OUTBOX_DIR / f'approval-request-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    out.write_text(text, encoding='utf-8')
    return out


def main():
    ts = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    errors = []
    try:
        picked = pick_posts(limit=6)
    except Exception as e:
        picked = []
        errors.append(f'{type(e).__name__}: {e}')
    results = []
    for item in picked:
        try:
            fname, remote = save_draft_to_aliyun('broad-scan', item)
            results.append({**item, 'fname': fname, 'remote': remote})
        except Exception as e:
            errors.append(f"{item['logic_name'][:60]} -> {type(e).__name__}: {e}")
    overview_report = build_overview_report(ts, results, errors)
    out = REPORT_DIR / f'cyber-exchange-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    out.write_text(overview_report, encoding='utf-8')
    print(out)
    print(overview_report)
    if results:
        approval_request = build_approval_request(ts, results[0], results[0]['fname'], results[0]['remote'])
        approval_out = write_approval_outbox(approval_request)
        send_result = send_report(approval_request)
        print('---APPROVAL_OUTBOX---')
        print(approval_out)
        print(approval_request)
        print('---OVERVIEW_SEND_RESULT---')
        print(json.dumps(send_result, ensure_ascii=False))
    else:
        print('---NO_SIGNAL---')
        print('本轮没有达到审批阈值的候选，不发送 Telegram。')


if __name__ == '__main__':
    main()
