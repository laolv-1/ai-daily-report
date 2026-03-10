#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import subprocess
from io import StringIO

import requests

ALIYUN_MYSQL_PASSWORD = os.getenv('ALIYUN_MYSQL_PASSWORD', '7c8a1c78902e5035')
BOT_TOKEN = os.getenv('LAFU_BOT_TOKEN', '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0')
CHAT_ID = os.getenv('LAFU_CHAT_ID', '7392107275')
LOG_PATH = '/var/log/laifu_market_research_runtime.log'
TELEGRAM_API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://b.apiepay.cn/tg_bridge_api')


def local_mysql(sql):
    out = subprocess.check_output(['mysql', '-uroot', '-p%s' % ALIYUN_MYSQL_PASSWORD, '-Nse', sql], universal_newlines=True)
    return out


def fetch_internal(limit=12):
    sql = (
        "SELECT source,title,url,anxiety_score,DATE_FORMAT(COALESCE(published_at,created_at),'%Y-%m-%d %H:%i') "
        "FROM intel_station.intel_articles "
        "WHERE COALESCE(published_at,created_at)>=DATE_SUB(NOW(),INTERVAL 72 HOUR) "
        "ORDER BY anxiety_score DESC, COALESCE(published_at,created_at) DESC "
        "LIMIT {limit};"
    ).format(limit=limit)
    raw = local_mysql(sql)
    rows = []
    for row in csv.reader(StringIO(raw), delimiter='\t'):
        if len(row) < 5:
            continue
        rows.append({'source': row[0], 'title': row[1], 'url': row[2], 'score': int(row[3] or 0), 'created': row[4]})
    return rows


def fetch_overseas(limit=12):
    sql = (
        "SELECT platform,signal_title,signal_url,signal_score,DATE_FORMAT(captured_at,'%Y-%m-%d %H:%i') "
        "FROM intel_station.raw_signals "
        "WHERE captured_at>=DATE_SUB(NOW(),INTERVAL 24 HOUR) "
        "ORDER BY signal_score DESC, captured_at DESC "
        "LIMIT {limit};"
    ).format(limit=limit)
    raw = local_mysql(sql)
    rows = []
    for row in csv.reader(StringIO(raw), delimiter='\t'):
        if len(row) < 5:
            continue
        rows.append({'platform': row[0], 'title': row[1], 'url': row[2], 'score': int(row[3] or 0), 'created': row[4]})
    return rows


def cut(text, n=30):
    text = str(text or '').strip()
    return text if len(text) <= n else text[:n-1] + '…'


def build_report(internal_rows, overseas_rows):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M BJT')
    top_internal = internal_rows[0] if internal_rows else None
    top_overseas = overseas_rows[0] if overseas_rows else None
    lines = [
        '🔥 **虾小侠 ClawWork 三阶获利审计**',
        '**生成时间：** {now}'.format(now=now),
        '',
        '💼 **存量资产变现**',
        '核心命题：用本体、来福、HK、Win10 直接打包自动化部署、巡检、日报系统服务。',
        'ROI判断：成本最低，最适合从 $10 原始单位起跳。',
        '执行动作：先做 1 套标准化演示页、交付清单和报价卡。',
        '',
        '🛰️ **轻投资扩军**',
    ]
    if top_internal:
        lines += [
            '核心命题：围绕「{title}」扩 1 到 2 个端侧节点做演示交付。'.format(title=cut(top_internal['title'], 26)),
            'ROI判断：节点成本低于新增服务溢价，边际收益更优。',
            '执行动作：先测新增节点报价，再与运维套餐绑定。',
        ]
    else:
        lines += [
            '核心命题：先补 1 到 2 个轻量 A2A 节点，扩展示与代运维产能。',
            'ROI判断：轻投资即可放大交付能力。',
            '执行动作：先核单节点回本周期，再决定扩编速度。',
        ]
    lines += ['', '🖥️ **重资产配置**']
    if top_overseas:
        lines += [
            '核心命题：围绕「{title}」评估 GPU 与高算力资产窗口。'.format(title=cut(top_overseas['title'], 26)),
            'ROI判断：上限高，但必须先验证稳定订单，不然折旧会反噬利润。',
            '执行动作：只有在持续接单后，再考虑 4090 或高算力节点。',
        ]
    else:
        lines += [
            '核心命题：GPU 与高算力适合后置，不适合现阶段抢跑。',
            'ROI判断：回本依赖连续订单，过早重投风险大。',
            '执行动作：先放大轻交付，再决定是否上矿机或高算力。',
        ]
    return '\n'.join(lines)


def send_report(text):
    r = requests.post('%s/bot%s/sendMessage' % (TELEGRAM_API_BASE.rstrip('/'), BOT_TOKEN), json={'chat_id': CHAT_ID, 'text': text[:3800], 'disable_web_page_preview': True}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(r.text)
    return data


def main():
    internal_rows = fetch_internal()
    overseas_rows = fetch_overseas()
    report = build_report(internal_rows, overseas_rows)
    tg = send_report(report)
    with open(LOG_PATH, 'a') as f:
        f.write(report + '\n\n')
    print(json.dumps({'telegram_message_id': tg['result']['message_id'], 'internal_count': len(internal_rows), 'overseas_count': len(overseas_rows), 'executor': 'laifu'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
