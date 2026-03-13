#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
来福直销弹药每日生成器 (C 轨核心)
- 读取当日副业焦虑/搞钱痛点信号
- 生成：闲鱼首发商品文案 + 小红书引流笔记
- 09:30 定时触发并推送 TG
"""
import json
import os
from datetime import datetime
from pathlib import Path

RAW_DIR = Path('/root/intelligence_hub/outputs/raw')
OUTPUT_DIR = Path('/root/intelligence_hub/outputs/daily_copy')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TG 环境变量（建议写入环境）
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN', '8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0')
TG_CHAT_ID = os.getenv('TG_CHAT_ID', '7392107275')

PERSONA = '冷静降维 + 毒舌短评 + 自动化服务出口'


def load_signals(today: str):
    """从原始抓取中提取副业焦虑/搞钱痛点信号"""
    signals = []
    for f in RAW_DIR.glob(f"*{today}*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            # 兼容不同结构
            items = data.get('items', []) if isinstance(data, dict) else []
            for it in items:
                title = it.get('title') or it.get('headline') or ''
                summary = it.get('summary') or it.get('desc') or ''
                if title or summary:
                    signals.append({'title': title, 'summary': summary, 'source': it.get('source','')})
        except Exception:
            continue
    return signals[:30]


def build_sales_bundle(signals):
    """
    TODO: 替换为 gpt-5.2-codex 生成
    结构必须包含：闲鱼文案 + 小红书笔记
    """
    pain = signals[0]['title'] if signals else '副业焦虑/信息差/短视频变现'
    xianyu = {
        'title': f'【代搭建】情报站/短视频脚本/小红书引流一条龙｜{pain}',
        'price': '399-2999',
        'hook': '包部署/可私有化/送3天维护/可接你现有号',
        'body': '你焦虑的不是没钱，是没“自动赚钱的系统”。我直接搭建：情报抓取→洗稿→脚本→分发。'
    }
    xhs = {
        'title': '我把“信息差”做成自动流水线后，副业焦虑直接消失',
        'tags': ['副业', '信息差', '自动化', '引流', '情报站'],
        'body': '别再盯着热门话题发呆了。真正能挣钱的是“自动系统”。我已经把它做成流水线。'
    }
    return {'xianyu': xianyu, 'xiaohongshu': xhs}


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    signals = load_signals(today)
    bundle = build_sales_bundle(signals)

    output = {
        'date': today,
        'generated_at': datetime.now().isoformat(),
        'persona': PERSONA,
        'bundle': bundle
    }

    out_file = OUTPUT_DIR / f'sales_bundle_{today}.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[OK] 直销弹药已生成: {out_file}')
    return out_file


if __name__ == '__main__':
    main()
