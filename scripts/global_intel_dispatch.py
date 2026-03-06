#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import re
import sys
from io import StringIO
from pathlib import Path

import paramiko
import requests

ROOT = Path('/root/.openclaw/workspace')
REPORT_DIR = ROOT / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

ALIYUN_HOST = os.getenv('ALIYUN_HOST', '100.82.179.92')
ALIYUN_USER = os.getenv('ALIYUN_USER', 'root')
ALIYUN_PASSWORD = os.getenv('ALIYUN_PASSWORD', '8ce42842#')
ALIYUN_MYSQL_PASSWORD = os.getenv('ALIYUN_MYSQL_PASSWORD', '7c8a1c78902e5035')

MODEL_BASE = os.getenv('LCK_BASE_URL', 'http://74.48.182.210:8317/v1')
MODEL_KEY = os.getenv('LCK_API_KEY', 'xDjn0xIm6ztThd8pSexN8CmCRttLtt8T')
MODEL_NAME = os.getenv('LCK_MODEL', 'gpt-5.4')

SUBREDDITS = [
    ('SaaS', 'hot'),
    ('Stripe', 'top?t=day'),
    ('cybersecurity', 'hot'),
]

KEYWORDS_GOOD = [
    'ban', 'blocked', 'chargeback', 'fraud', 'suspend', 'suspension', 'kyc', 'compliance',
    'breach', 'attack', 'outage', 'exploit', 'vulnerability', 'stripe', 'payment', 'saas',
    'detection', 'account', 'risk', 'security', 'malware', 'bot', 'refund', 'policy'
]
KEYWORDS_BAD = [
    'meme', 'shitpost', 'roast', 'hiring', 'career', 'weekly thread', 'off topic', 'funny'
]


def score_post(p: dict) -> int:
    title = (p.get('title') or '').lower()
    score = int(p.get('score') or 0)
    comments = int(p.get('num_comments') or 0)
    ups = int(score / 10) + comments * 2
    for kw in KEYWORDS_GOOD:
        if kw in title:
            ups += 18
    for kw in KEYWORDS_BAD:
        if kw in title:
            ups -= 25
    if p.get('stickied'):
        ups -= 20
    if p.get('over_18'):
        ups -= 10
    return ups


def fetch_reddit(limit_per_sub: int = 10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) OpenClawGlobalIntel/1.0',
        'Accept': 'application/json',
    }
    picked = []
    for sub, mode in SUBREDDITS:
        urls = [
            f'https://www.reddit.com/r/{sub}/{mode}.json&limit={limit_per_sub}&raw_json=1' if '?' in mode else f'https://www.reddit.com/r/{sub}/{mode}.json?limit={limit_per_sub}&raw_json=1',
            f'https://www.reddit.com/r/{sub}.json?limit={limit_per_sub}&raw_json=1',
        ]
        data = None
        last_err = None
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=20)
                r.raise_for_status()
                data = r.json()['data']['children']
                break
            except Exception as e:
                last_err = e
                continue
        if data is None:
            print(f'[reddit-skip] r/{sub} -> {type(last_err).__name__}: {last_err}', file=sys.stderr)
            continue
        for item in data:
            p = item['data']
            post = {
                'subreddit': sub,
                'title': p.get('title', ''),
                'url': 'https://reddit.com' + p.get('permalink', ''),
                'score': int(p.get('score') or 0),
                'comments': int(p.get('num_comments') or 0),
                'created': dt.datetime.fromtimestamp(p.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M'),
                'selftext': re.sub(r'\s+', ' ', (p.get('selftext') or ''))[:500],
            }
            post['signal_score'] = score_post(p)
            if post['signal_score'] >= 20:
                picked.append(post)
    picked.sort(key=lambda x: (x['signal_score'], x['score'], x['comments']), reverse=True)
    return picked[:8]


def ssh_exec(host: str, user: str, password: str, cmd: str, timeout: int = 30) -> str:
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=host, username=user, password=password, timeout=10, banner_timeout=10, auth_timeout=10)
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    cli.close()
    if err.strip() and 'Using a password on the command line interface can be insecure.' not in err:
        raise RuntimeError(err)
    return out


def fetch_domestic(limit: int = 8):
    sql = (
        "SELECT id,category,source,title,url,anxiety_score,"
        "DATE_FORMAT(COALESCE(published_at,created_at),'%Y-%m-%d %H:%i') "
        "FROM intel_station.intel_articles "
        "WHERE COALESCE(published_at,created_at)>=DATE_SUB(NOW(),INTERVAL 72 HOUR) "
        "ORDER BY anxiety_score DESC, COALESCE(published_at,created_at) DESC "
        f"LIMIT {limit};"
    )
    cmd = f"mysql -uroot -p'{ALIYUN_MYSQL_PASSWORD}' -Nse \"{sql}\""
    raw = ssh_exec(ALIYUN_HOST, ALIYUN_USER, ALIYUN_PASSWORD, cmd, timeout=40)
    rows = []
    reader = csv.reader(StringIO(raw), delimiter='\t')
    for row in reader:
        if len(row) < 7:
            continue
        rows.append({
            'id': row[0],
            'category': row[1],
            'source': row[2],
            'title': row[3],
            'url': row[4],
            'anxiety_score': int(row[5] or 0),
            'created': row[6],
        })
    return rows


def summarize_with_model(domestic, reddit):
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': '你是情报总控官。请把国内风控/平台动态与海外 Reddit 风险讨论融合成一份精炼但有判断力的日报。输出必须是中文，避免空话，给出明确风险、映射和行动建议。'
            },
            {
                'role': 'user',
                'content': json.dumps({'domestic': domestic, 'reddit': reddit}, ensure_ascii=False)
            }
        ],
        'temperature': 0.4
    }
    url = MODEL_BASE.rstrip('/') + '/chat/completions'
    r = requests.post(url, headers={'Authorization': f'Bearer {MODEL_KEY}'}, json=prompt, timeout=90)
    r.raise_for_status()
    data = r.json()
    return data['choices'][0]['message']['content'].strip()


def fallback_summary(domestic, reddit):
    lines = ['【总览】', '今天国内侧偏平台风控/技术话题，海外侧偏支付、合规、安全风险。建议把支付、封号、攻击面三条线合并观察。']
    lines.append('')
    lines.append('【国内映射】')
    for item in domestic[:5]:
        lines.append(f"- {item['category']}｜{item['title']}（{item['source']}，焦虑分 {item['anxiety_score']}）")
    lines.append('')
    lines.append('【海外 Reddit Digest】')
    for item in reddit[:5]:
        lines.append(f"- r/{item['subreddit']}｜{item['title']}（热度 {item['score']} / 评论 {item['comments']}）")
    lines.append('')
    lines.append('【动作建议】')
    lines.append('- 盯支付合规、账户风控、漏洞披露三条线。')
    lines.append('- 国内舆情若出现平台政策收紧，优先映射到 Stripe/KYC/封号链路。')
    return '\n'.join(lines)


def render_report(domestic, reddit, summary):
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M %Z')
    lines = [f'🔥 全球双擎情报日报', f'生成时间：{now}', '']
    lines.append('## 深度总结')
    lines.append(summary)
    lines.append('')
    lines.append('## 国内情报矿场（阿里云）')
    for item in domestic:
        lines.append(f"- [{item['category']}] {item['title']}｜{item['source']}｜焦虑分 {item['anxiety_score']}｜{item['created']}\n  {item['url']}")
    lines.append('')
    lines.append('## 海外 Reddit Digest（VPS）')
    for item in reddit:
        lines.append(f"- [r/{item['subreddit']}] {item['title']}｜热度 {item['score']}｜评论 {item['comments']}｜信号分 {item['signal_score']}｜{item['created']}\n  {item['url']}")
    return '\n'.join(lines)


def main():
    domestic = fetch_domestic()
    reddit = fetch_reddit()
    try:
        summary = summarize_with_model(domestic, reddit)
    except Exception as e:
        summary = fallback_summary(domestic, reddit) + f"\n\n【模型降级回执】{type(e).__name__}: {e}"
    report = render_report(domestic, reddit, summary)
    ts = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    out = REPORT_DIR / f'global-intel-{ts}.md'
    latest = REPORT_DIR / 'global-intel-latest.md'
    out.write_text(report, encoding='utf-8')
    latest.write_text(report, encoding='utf-8')
    print(str(out))
    print('---REPORT---')
    print(report)


if __name__ == '__main__':
    main()
