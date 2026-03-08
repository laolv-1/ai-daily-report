#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import re
import shutil
import tempfile
from io import StringIO
from pathlib import Path

import paramiko
import requests

from github_sync_helper import commit_and_push, copy_into_repo, dated_rel_path

ROOT = Path('/root/.openclaw/workspace')
ALIYUN_HOST = '100.82.179.92'
ALIYUN_USER = 'root'
ALIYUN_PASSWORD = '8ce42842#'
ALIYUN_MYSQL_PASSWORD = '7c8a1c78902e5035'
LAFU_BOT_TOKEN = os.getenv('LAFU_BOT_TOKEN', '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0')
LAFU_CHAT_ID = os.getenv('LAFU_CHAT_ID', '7392107275')
WIN_HOST = '100.89.160.67'
WIN_USER = 'Administrator'
WIN_PASSWORD = 'As1231'
WIN_BASE = 'D:/来财/市场调研'
LOG_PATH = ROOT / 'memory' / 'market_research_daily.log'
STATE_PATH = ROOT / 'memory' / 'market_research_daily_state.json'

SUBREDDITS = [
    ('Entrepreneur', 'hot'),
    ('SaaS', 'hot'),
    ('smallbusiness', 'hot'),
    ('Fiverr', 'hot'),
    ('Upwork', 'hot'),
]


def log(msg: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(f'[{stamp}] {msg}\n')


def ssh_exec(cmd: str, timeout: int = 40) -> str:
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


def fetch_internal(limit: int = 10):
    sql = (
        "SELECT source,title,url,anxiety_score,DATE_FORMAT(COALESCE(published_at,created_at),'%Y-%m-%d %H:%i') "
        "FROM intel_station.intel_articles "
        "WHERE COALESCE(published_at,created_at)>=DATE_SUB(NOW(),INTERVAL 72 HOUR) "
        "ORDER BY anxiety_score DESC, COALESCE(published_at,created_at) DESC "
        f"LIMIT {limit};"
    )
    raw = ssh_exec(f"mysql -uroot -p'{ALIYUN_MYSQL_PASSWORD}' -Nse \"{sql}\"")
    rows = []
    for row in csv.reader(StringIO(raw), delimiter='\t'):
        if len(row) < 5:
            continue
        rows.append({
            'source': row[0], 'title': row[1], 'url': row[2], 'anxiety_score': int(row[3] or 0), 'created': row[4]
        })
    return rows


def fetch_reddit(limit_per_sub: int = 8):
    headers = {'User-Agent': 'Mozilla/5.0 OpenClawMarketResearch/1.0', 'Accept': 'application/json'}
    out = []
    seen = set()
    for sub, mode in SUBREDDITS:
        url = f'https://www.reddit.com/r/{sub}/{mode}.json?limit={limit_per_sub}&raw_json=1'
        try:
            r = requests.get(url, headers=headers, timeout=28)
            r.raise_for_status()
            data = r.json()['data']['children']
        except Exception as e:
            log(f'REDDIT_SKIP {sub} {type(e).__name__}: {e}')
            continue
        for item in data:
            p = item['data']
            title = re.sub(r'\s+', ' ', p.get('title', '')).strip()
            if not title:
                continue
            key = (sub, title)
            if key in seen:
                continue
            seen.add(key)
            score = int(p.get('score') or 0)
            comments = int(p.get('num_comments') or 0)
            signal = score + comments * 3
            if signal < 80:
                continue
            out.append({
                'platform': f'reddit/r/{sub}',
                'title': title,
                'url': 'https://reddit.com' + p.get('permalink', ''),
                'score': score,
                'comments': comments,
                'signal': signal,
            })
    out.sort(key=lambda x: (x['signal'], x['score'], x['comments']), reverse=True)
    return out[:12]


def pick_internal_signals(rows):
    picks = []
    for row in rows:
        title = row['title']
        if 'OpenClaw' in title or '小龙虾' in title or 'AI' in title or '机器人' in title:
            picks.append(row)
    return picks[:6] if picks else rows[:4]


def build_rows(internal_rows, reddit_rows):
    internal = pick_internal_signals(internal_rows)
    rows = []
    rows.append({
        '赛道/平台': '闲鱼 / 抖音 / 小红书',
        '成本档位': 'Tier 0',
        'AI 变现玩法': '用现有 VPS+手机+Win10 批量做 AI 代写、封面、二改脚本与私域引流接单。',
        '需增加的A2A设备': '无需新增；直接用现有手机与 Win10 做分发。',
        '预期收益与风控': '收益：快启单；风控：平台限流与私信骚扰，必须控频。',
    })
    rows.append({
        '赛道/平台': 'Fiverr / Upwork',
        '成本档位': 'Tier 0',
        'AI 变现玩法': '包装为 AI 自动化代搭建、客服机器人、日报系统与风控巡检服务接海外单。',
        '需增加的A2A设备': '无需新增；现有 VPS + 来福可做交付与演示。',
        '预期收益与风控': '收益：客单高于中文区；风控：账号新号冷启动慢，需作品集。',
    })
    rows.append({
        '赛道/平台': 'Telegram / Discord 社群',
        '成本档位': 'Tier 1',
        'AI 变现玩法': '做自动情报雷达、社群摘要、群控机器人，按订阅收费。',
        '需增加的A2A设备': '加 1 台便宜云主机或流量卡设备，做多节点分发。',
        '预期收益与风控': '收益：订阅制稳定；风控：群控过猛会封禁，需限速与白名单。',
    })
    rows.append({
        '赛道/平台': 'TikTok / YouTube Shorts',
        '成本档位': 'Tier 1',
        'AI 变现玩法': '用 AI 批量做选题、脚本、配音、封面，跑短视频矩阵引流卖服务或联盟单。',
        '需增加的A2A设备': '建议加 1-2 台二手手机或海外代理资源。',
        '预期收益与风控': '收益：放大最快；风控：搬运和低质内容易限流。',
    })
    rows.append({
        '赛道/平台': '独立站 / SaaS 工具站',
        '成本档位': 'Tier 2',
        'AI 变现玩法': '围绕 OpenClaw 代部署、风险巡检、Agent 运维面板做订阅型 SaaS。',
        '需增加的A2A设备': '建议加 Mac Mini 或更强长期母舰，支撑多客户、多节点演示。',
        '预期收益与风控': '收益：复利高；风控：运维复杂、售后重，需标准化交付。',
    })
    rows.append({
        '赛道/平台': 'GPU 算力 / 本地模型服务',
        '成本档位': 'Tier 2',
        'AI 变现玩法': '自建 4090/云 GPU 节点，对外卖推理、训练、Agent 批处理能力。',
        '需增加的A2A设备': '4090 矿机或可计费 GPU 云节点。',
        '预期收益与风控': '收益：上限高；风控：前期投入重，需求波动大。',
    })

    if internal:
        top = internal[0]
        rows.append({
            '赛道/平台': f"内部风向：{top['source']}",
            '成本档位': 'Tier 0',
            'AI 变现玩法': f"顺着《{top['title'][:22]}》热度做解读号、教程号或部署代搭建。",
            '需增加的A2A设备': '无需新增，先用现有内容与分发链路截流。',
            '预期收益与风控': '收益：蹭热点转化快；风控：热点消退也快，必须当天出击。',
        })
    if reddit_rows:
        top = reddit_rows[0]
        rows.append({
            '赛道/平台': top['platform'],
            '成本档位': 'Tier 1',
            'AI 变现玩法': f"围绕“{top['title'][:26]}”做海外自动化代理、提示词审计或工作流代搭。",
            '需增加的A2A设备': '建议加海外节点或演示专用账号资源。',
            '预期收益与风控': '收益：海外需求真；风控：交付边界不清会拉长售后。',
        })
    return rows


def render_report(rows):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M BJT')
    lines = [
        '🔥 每日AI变现与A2A扩军调研报告',
        f'生成时间：{now}',
        '',
        '| 赛道/平台 | 成本档位 | AI 变现玩法 | 需增加的A2A设备 | 预期收益与风控 |',
        '|---|---|---|---|---|',
    ]
    for row in rows:
        vals = [row['赛道/平台'], row['成本档位'], row['AI 变现玩法'], row['需增加的A2A设备'], row['预期收益与风控']]
        vals = [str(v).replace('\n', ' ').replace('|', '｜') for v in vals]
        lines.append('| ' + ' | '.join(vals) + ' |')
    return '\n'.join(lines)


def send_to_laifu(report: str):
    url = f'https://api.telegram.org/bot{LAFU_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': LAFU_CHAT_ID, 'text': report[:3900], 'disable_web_page_preview': True}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(r.text)
    return data


def push_to_win10(report: str):
    date_str = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d')
    remote_file = f'{WIN_BASE}/{date_str}_ClawWork.md'
    tmp = tempfile.NamedTemporaryFile('w', delete=False, suffix='.md', encoding='utf-8')
    try:
        tmp.write(report)
        tmp.close()
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect(hostname=WIN_HOST, username=WIN_USER, password=WIN_PASSWORD, timeout=10, banner_timeout=10, auth_timeout=10)
        try:
            cmd = f'powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path \'{WIN_BASE}\' | Out-Null"'
            stdin, stdout, stderr = cli.exec_command(cmd, timeout=20)
            _ = stdout.read().decode('utf-8', 'ignore')
            err = stderr.read().decode('utf-8', 'ignore')
            if err.strip():
                raise RuntimeError(err)
            sftp = cli.open_sftp()
            try:
                sftp.put(tmp.name, remote_file)
                with sftp.open(remote_file, 'r') as f:
                    data = f.read()
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', 'ignore')
            finally:
                sftp.close()
        finally:
            cli.close()
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
    return remote_file, len(data)


def sync_to_github(report: str) -> dict:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    tmp = ROOT / 'memory' / '_market_research_github.md'
    tmp.write_text(report, encoding='utf-8')
    try:
        rel = dated_rel_path('market-research', f'{now.strftime("%Y-%m-%d")}_ClawWork.md')
        copy_into_repo(tmp, rel)
        return commit_and_push(f'市场调研: {now.strftime("%Y-%m-%d %H:%M:%S BJT")}')
    finally:
        tmp.unlink(missing_ok=True)


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def cleanup_local_artifacts():
    pycache = ROOT / 'scripts' / '__pycache__'
    if pycache.exists():
        shutil.rmtree(pycache, ignore_errors=True)


def main():
    internal = fetch_internal()
    reddit = fetch_reddit()
    rows = build_rows(internal, reddit)
    report = render_report(rows)
    tg = send_to_laifu(report)
    remote_file, size = push_to_win10(report)
    github = sync_to_github(report)
    cleanup_local_artifacts()
    state = {
        'last_run_bjt': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'telegram_message_id': tg['result']['message_id'],
        'win10_remote_file': remote_file,
        'win10_size': size,
        'internal_count': len(internal),
        'reddit_count': len(reddit),
        'github': github,
    }
    save_state(state)
    log(f"OK tg_message_id={state['telegram_message_id']} win10={remote_file} size={size} internal={len(internal)} reddit={len(reddit)} github={json.dumps(github, ensure_ascii=False)}")
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    main()
