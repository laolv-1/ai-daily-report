#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import re
from io import StringIO

import paramiko
import requests

ALIYUN_HOST = os.getenv('ALIYUN_HOST', '100.82.179.92')
ALIYUN_USER = os.getenv('ALIYUN_USER', 'root')
ALIYUN_PASSWORD = os.getenv('ALIYUN_PASSWORD', '8ce42842#')
ALIYUN_MYSQL_PASSWORD = os.getenv('ALIYUN_MYSQL_PASSWORD', '7c8a1c78902e5035')

MODEL_BASE = os.getenv('LCK_BASE_URL', 'http://74.48.182.210:8317/v1')
MODEL_KEY = os.getenv('LCK_API_KEY', 'xDjn0xIm6ztThd8pSexN8CmCRttLtt8T')
MODEL_NAME = os.getenv('LCK_MODEL', 'gpt-5.2-codex')

TELEGRAM_BOT_TOKEN = os.getenv('LAFU_BOT_TOKEN', '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0')
TELEGRAM_CHAT_ID = os.getenv('LAFU_CHAT_ID', '7392107275')
TELEGRAM_API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://b.apiepay.cn/tg_bridge_api')

SUBREDDITS = [
    ('SaaS', 'hot'),
    ('Stripe', 'top?t=day'),
    ('cybersecurity', 'hot'),
]

KEYWORDS_GOOD = [
    'ban', 'blocked', 'chargeback', 'fraud', 'suspend', 'suspension', 'kyc', 'compliance',
    'breach', 'attack', 'outage', 'exploit', 'vulnerability', 'stripe', 'payment', 'saas',
    'detection', 'account', 'risk', 'security', 'malware', 'bot', 'refund', 'policy',
    'automation', 'agent', 'deploy', 'workflow', 'ai'
]
KEYWORDS_BAD = [
    'meme', 'shitpost', 'roast', 'hiring', 'career', 'weekly thread', 'off topic', 'funny',
    'monthly post', 'mentorship monday', 'deals + offers', 'iptv'
]


def ssh_exec(cmd: str, timeout: int = 60) -> str:
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=ALIYUN_HOST, username=ALIYUN_USER, password=ALIYUN_PASSWORD, timeout=10, banner_timeout=10, auth_timeout=10)
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    cli.close()
    cleaned_err = '\n'.join(line for line in err.splitlines() if 'Using a password on the command line interface can be insecure.' not in line).strip()
    if cleaned_err:
        raise RuntimeError(cleaned_err)
    return out


def score_post(p: dict) -> int:
    title = (p.get('title') or '').lower()
    score = int(p.get('score') or 0)
    comments = int(p.get('num_comments') or 0)
    val = int(score / 10) + comments * 2
    for kw in KEYWORDS_GOOD:
        if kw in title:
            val += 18
    for kw in KEYWORDS_BAD:
        if kw in title:
            val -= 80
    if p.get('stickied'):
        val -= 40
    if p.get('over_18'):
        val -= 10
    return val


def fetch_reddit(limit_per_sub: int = 10):
    headers = {
        'User-Agent': 'Mozilla/5.0 OpenClawGlobalIntel/2.0',
        'Accept': 'application/json',
    }
    picked = []
    seen = set()
    for sub, mode in SUBREDDITS:
        url = f'https://www.reddit.com/r/{sub}/{mode}.json&limit={limit_per_sub}&raw_json=1' if '?' in mode else f'https://www.reddit.com/r/{sub}/{mode}.json?limit={limit_per_sub}&raw_json=1'
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()['data']['children']
        except Exception:
            continue
        for item in data:
            p = item['data']
            permalink = p.get('permalink', '')
            if not permalink or permalink in seen:
                continue
            seen.add(permalink)
            post = {
                'source_node': 'laicai',
                'source_type': 'overseas_trend',
                'platform': f'reddit/r/{sub}',
                'signal_title': re.sub(r'\s+', ' ', p.get('title', '')).strip(),
                'signal_url': 'https://reddit.com' + permalink,
                'signal_body': re.sub(r'\s+', ' ', (p.get('selftext') or ''))[:1200],
                'signal_score': score_post(p),
                'signal_tags': '海外,趋势,自动化,变现',
                'captured_at': dt.datetime.fromtimestamp(p.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'extra_json': '',
            }
            if post['signal_score'] >= 40 and post['signal_title']:
                picked.append(post)
    picked.sort(key=lambda x: x['signal_score'], reverse=True)
    return picked[:8]


def ingest_raw_signals(rows):
    if not rows:
        return 0
    values = []
    for r in rows:
        def esc(v):
            return str(v or '').replace('\\', '\\\\').replace("'", "\\'")
        values.append(
            "('laicai','%s','%s','%s','%s','%s',%d,'%s','%s',NULL)" % (
                esc(r['source_type']), esc(r['platform']), esc(r['signal_title']), esc(r['signal_url']),
                esc(r['signal_body']), int(r['signal_score']), esc(r['signal_tags']), esc(r['captured_at'])
            )
        )
    sql = (
        "INSERT INTO intel_station.raw_signals "
        "(source_node,source_type,platform,signal_title,signal_url,signal_body,signal_score,signal_tags,captured_at,extra_json) VALUES "
        + ','.join(values) + '; SELECT ROW_COUNT();'
    )
    out = ssh_exec(f"mysql -uroot -p'{ALIYUN_MYSQL_PASSWORD}' -Nse \"{sql}\"", timeout=80).strip()
    try:
        return int(out.splitlines()[-1])
    except Exception:
        return len(rows)


def fetch_domestic(limit: int = 6):
    sql = (
        "SELECT category,title,anxiety_score,DATE_FORMAT(COALESCE(published_at,created_at),'%Y-%m-%d %H:%i') "
        "FROM intel_station.intel_articles "
        "WHERE COALESCE(published_at,created_at)>=DATE_SUB(NOW(),INTERVAL 72 HOUR) "
        "ORDER BY anxiety_score DESC, COALESCE(published_at,created_at) DESC "
        f"LIMIT {limit};"
    )
    raw = ssh_exec(f"mysql -uroot -p'{ALIYUN_MYSQL_PASSWORD}' -Nse \"{sql}\"", timeout=40)
    rows = []
    for row in csv.reader(StringIO(raw), delimiter='\t'):
        if len(row) < 4:
            continue
        rows.append({'category': row[0], 'title': row[1], 'score': int(row[2] or 0), 'created': row[3]})
    return rows


def fallback_summary(domestic, overseas):
    lines = ['🔥 来福双擎情报日报', f"生成时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", '', '## 🇨🇳 国内资金与流量', '| 风险级别 | 核心事件 | 主公对策 |', '|---|---|---|']
    if domestic:
        for x in domestic[:4]:
            level = '高' if x['score'] >= 18 else ('中' if x['score'] >= 10 else '低')
            title = (x['title'][:24] + '…') if len(x['title']) > 24 else x['title']
            lines.append(f"| {level} | {x['category']}：{title} | 盯链路、看影响、准备复核 |")
    else:
        lines.append('| 低 | 国内侧暂无高压新增 | 保持巡航，不加动作 |')
    lines += ['', '## 🇺🇸 海外硬核与漏洞', '| 风险级别 | 核心事件 | 主公对策 |', '|---|---|---|']
    if overseas:
        for x in overseas[:4]:
            level = '高' if x['signal_score'] >= 90 else ('中' if x['signal_score'] >= 60 else '低')
            title = (x['signal_title'][:24] + '…') if len(x['signal_title']) > 24 else x['signal_title']
            lines.append(f"| {level} | {x['platform']}：{title} | 入来福 raw_signals，等主编提纯 |")
    else:
        lines.append('| 低 | 海外侧暂无高信号新增 | 继续探针，不做扩写 |')
    return '\n'.join(lines)


def summarize_with_model(domestic, overseas):
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {'role': 'system', 'content': '你是情报总控官。只输出中文 Markdown。必须只有两个区块：## 🇨🇳 国内资金与流量、## 🇺🇸 海外硬核与漏洞。每个区块下只能是表格，表头固定为 | 风险级别 | 核心事件 | 主公对策 | 。每区块最多4行，禁止前言总结。'},
            {'role': 'user', 'content': json.dumps({'domestic': domestic, 'overseas': overseas}, ensure_ascii=False)}
        ],
        'temperature': 0.2,
    }
    r = requests.post(MODEL_BASE.rstrip('/') + '/chat/completions', headers={'Authorization': f'Bearer {MODEL_KEY}'}, json=prompt, timeout=90)
    r.raise_for_status()
    text = r.json()['choices'][0]['message']['content'].strip()
    if '## 🇨🇳 国内资金与流量' not in text or '## 🇺🇸 海外硬核与漏洞' not in text:
        raise RuntimeError('summary shape invalid')
    return '🔥 来福双擎情报日报\n生成时间：%s\n\n%s' % (dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text)


def tg_card_report(domestic, overseas):
    lines = ['🔥 **来福双擎情报日报**', '**生成时间：** %s' % dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '', '🇨🇳 **国内资金与流量**']
    if domestic:
        for x in domestic[:4]:
            level = '高' if x['score'] >= 18 else ('中' if x['score'] >= 10 else '低')
            title = (x['title'][:24] + '…') if len(x['title']) > 24 else x['title']
            lines += ['风险级别：**%s**' % level, '核心事件：%s：%s' % (x['category'], title), '主公对策：盯链路、看影响、准备复核', '']
    else:
        lines += ['风险级别：**低**', '核心事件：国内侧暂无高压新增', '主公对策：保持巡航，不加动作', '']
    lines += ['🇺🇸 **海外硬核与漏洞**']
    if overseas:
        for x in overseas[:4]:
            level = '高' if x['signal_score'] >= 90 else ('中' if x['signal_score'] >= 60 else '低')
            title = (x['signal_title'][:24] + '…') if len(x['signal_title']) > 24 else x['signal_title']
            lines += ['风险级别：**%s**' % level, '核心事件：%s：%s' % (x['platform'], title), '主公对策：入来福 raw_signals，等主编提纯', '']
    else:
        lines += ['风险级别：**低**', '核心事件：海外侧暂无高信号新增', '主公对策：继续探针，不做扩写', '']
    return '\n'.join(lines).strip()


def send_to_laifu(report: str):
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': report[:3800], 'disable_web_page_preview': True}
    r = requests.post("{}/bot{}/sendMessage".format(TELEGRAM_API_BASE.rstrip('/'), TELEGRAM_BOT_TOKEN), json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(r.text)
    return data


def main():
    overseas = fetch_reddit()
    inserted = ingest_raw_signals(overseas)
    domestic = fetch_domestic()
    try:
        _ = summarize_with_model(domestic, overseas)
    except Exception:
        pass
    report = tg_card_report(domestic, overseas)
    tg = send_to_laifu(report)
    overseas.clear()
    domestic.clear()
    print(json.dumps({'raw_signals_inserted': inserted, 'telegram_message_id': tg['result']['message_id'], 'local_persist': 'disabled'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
