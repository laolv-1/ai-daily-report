#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import subprocess
from io import StringIO
from pathlib import Path

import requests

ALIYUN_MYSQL_PASSWORD = os.getenv('ALIYUN_MYSQL_PASSWORD', '7c8a1c78902e5035')
MODEL_BASE = os.getenv('LCK_BASE_URL', 'http://74.48.182.210:8317/v1')
MODEL_KEY = os.getenv('LCK_API_KEY', 'xDjn0xIm6ztThd8pSexN8CmCRttLtt8T')
MODEL_NAME = os.getenv('LCK_MODEL', 'gpt-5.2-codex')
BOT_TOKEN = os.getenv('LAFU_BOT_TOKEN', '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0')
CHAT_ID = os.getenv('LAFU_CHAT_ID', '7392107275')
TELEGRAM_API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://b.apiepay.cn/tg_bridge_api')
SKILL_PATH = Path(os.getenv('XIAXIAOXIA_SKILL_PATH', '/root/openclaw-intel-workspace/skills/skill_xiaxiaoxia_persona_factory.md'))


def mysql_exec(sql):
    return subprocess.check_output(['mysql', '-uroot', '-p%s' % ALIYUN_MYSQL_PASSWORD, '-Nse', sql], universal_newlines=True)


def fetch_signal():
    sql = (
        "SELECT id,platform,signal_title,signal_body,signal_score,IFNULL(signal_tags,''),IFNULL(signal_url,'') FROM intel_station.raw_signals "
        "WHERE captured_at>=DATE_SUB(NOW(),INTERVAL 24 HOUR) ORDER BY signal_score DESC, captured_at DESC LIMIT 1;"
    )
    raw = mysql_exec(sql)
    rows = list(csv.reader(StringIO(raw), delimiter='\t'))
    if not rows:
        return None
    row = rows[0]
    return {
        'id': row[0],
        'platform': row[1],
        'title': row[2],
        'body': row[3],
        'score': int(row[4] or 0),
        'tags': row[5],
        'url': row[6],
    }


def load_skill_text():
    text = SKILL_PATH.read_text(encoding='utf-8')
    return text.strip()


def build_user_prompt(signal):
    return json.dumps({
        'task': '请严格依据 system message 中的 Persona 技能书生成 1 段 15-30 秒中文成片剧本，并确保隐含完成四段结构引擎：痛点暴击 -> 低效流程解构 -> 自动化降维打击预览 -> 业务网关入口。只输出最终成片正文，不要标题，不要解释，不要分段标签。',
        'raw_signal': signal,
    }, ensure_ascii=False)


def generate_script(signal):
    skill_text = load_skill_text()
    prompt = {
        'model': MODEL_NAME,
        'messages': [
            {'role': 'system', 'content': skill_text},
            {'role': 'user', 'content': build_user_prompt(signal)}
        ],
        'temperature': 0.7,
    }
    r = requests.post(MODEL_BASE.rstrip('/') + '/chat/completions', headers={'Authorization': 'Bearer %s' % MODEL_KEY}, json=prompt, timeout=90)
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content'].strip()


def build_tg_message(signal, content):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M BJT')
    lines = [
        '🦐 **虾小侠首秀剧本**',
        '**生成时间：** {now}'.format(now=now),
        '',
        '🎯 **信号源**',
        '{platform}｜评分 {score}'.format(platform=signal['platform'] or '未知', score=signal['score']),
        signal['title'],
        '',
        '🧠 **成片正文**',
        content,
    ]
    return '\n'.join(lines)


def send_tg(text):
    payload = {'chat_id': CHAT_ID, 'text': text[:3800], 'disable_web_page_preview': True}
    r = requests.post('%s/bot%s/sendMessage' % (TELEGRAM_API_BASE.rstrip('/'), BOT_TOKEN), json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(r.text)
    return data


def store_output(signal_id, content, tg_message_id=None):
    esc = lambda s: str(s or '').replace('\\', '\\\\').replace("'", "\\'")
    extra = json.dumps({'telegram_message_id': tg_message_id} if tg_message_id else {}, ensure_ascii=False)
    sql = (
        "INSERT INTO intel_station.editorial_outputs (source_signal_id,output_type,persona,title,content,style,status,generated_at,extra_json) VALUES "
        "(%d,'script_15_30s','虾小侠','赛博脱口秀首稿','%s','锋利理性 / 赛博降维 / 冷静毒舌','draft',NOW(),'%s'); SELECT LAST_INSERT_ID();" % (
            int(signal_id), esc(content), esc(extra)
        )
    )
    out = mysql_exec(sql)
    return out.strip().splitlines()[-1]


def main():
    signal = fetch_signal()
    if not signal:
        print(json.dumps({'status': 'NO_SIGNAL'}, ensure_ascii=False))
        return
    content = generate_script(signal)
    tg_text = build_tg_message(signal, content)
    tg = send_tg(tg_text)
    row_id = store_output(signal['id'], content, tg['result']['message_id'])
    print(json.dumps({
        'status': 'OK',
        'signal_id': signal['id'],
        'editorial_output_id': row_id,
        'telegram_message_id': tg['result']['message_id'],
        'skill_path': str(SKILL_PATH),
        'preview': content,
        'generated_at': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
