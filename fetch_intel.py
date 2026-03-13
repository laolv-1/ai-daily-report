#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 情报抓取脚本 - 来福机器人专用
功能：聚合多源情报，生成 daily_intel.json
无痕模式：随机 UA + 推送后清空缓存
"""

import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict

# 随机 User-Agent 池 (防风控)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

def get_random_headers() -> Dict[str, str]:
    """生成随机请求头 (无痕指纹)"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def fetch_mock_intel() -> List[Dict]:
    """
    模拟情报抓取 (实际部署时替换为真实爬虫)
    来福机器人应在此处接入：
    - Twitter API / Nitter
    - GitHub Trending
    - Hacker News
    - 币安/ CoinGecko API
    - 安全公告 RSS
    """
    # 示例：从环境变量或配置文件读取真实数据
    # 此处用占位数据演示
    return [
        {
            "title": "🚨 [自动抓取] OpenAI GPT-5.3 架构泄露",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Twitter/X",
            "summary": "内部文档显示 GPT-5.3 集成 O1 推理链，Q2 发布。",
            "tags": ["高危", "AI 模型"]
        },
        {
            "title": "💰 币安新上币分析",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "CoinGecko",
            "summary": "$WIF 24h 交易量破 5 亿，巨鲸地址累计买入 1200 万枚。",
            "tags": ["中危", "加密货币"]
        },
    ]

def generate_daily_report() -> Dict:
    """生成日报 JSON 结构"""
    intel_list = fetch_mock_intel()
    
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S GMT+8"),
        "source": "来福机器人 (Aliyun 100.82.179.92)",
        "intel": intel_list
    }
    
    return report

def cleanup_cache():
    """无痕清理：删除临时缓存文件"""
    cache_files = [
        "raw_twitter.json",
        "raw_github.json",
        "raw_hn.json",
        "temp_scrape.html",
    ]
    for f in cache_files:
        if os.path.exists(f):
            os.remove(f)
            print(f"🧹 已清理缓存：{f}")

def main():
    print("🤖 开始生成 AI 情报日报...")
    print(f"📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成报告
    report = generate_daily_report()
    
    # 写入 JSON
    output_file = "daily_intel.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 情报数据已写入：{output_file}")
    print(f"📊 共 {len(report['intel'])} 条情报")
    
    # 无痕清理
    cleanup_cache()
    
    print("🔒 缓存已清空，无痕模式完成")

if __name__ == "__main__":
    main()
