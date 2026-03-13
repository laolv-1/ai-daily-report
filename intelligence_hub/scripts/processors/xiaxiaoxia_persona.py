#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虾小侠人格洗稿处理器 (A 轨核心)
架构白皮书登记路径：/root/intelligence_hub/processors/xiaxiaoxia_persona.py
Cron: 0 7 * * * (每日 7:00 执行，抓取后 1 小时)
输入：/root/intelligence_hub/outputs/raw/*.json
产出：/root/intelligence_hub/outputs/json/intelligence_YYYY-MM-DD.json
"""

import json
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("/root/intelligence_hub/outputs/raw")
OUTPUT_DIR = Path("/root/intelligence_hub/outputs/json")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 虾小侠人格基线
XIA_XIAO_XIA_PERSONA = {
    "tone": "冷静降维、毒舌短评、高逻辑密度",
    "style": "自动化服务出口、不废话、直击痛点",
    "forbidden": ["过度情绪化", "无意义感叹", "表演性分析"]
}

def xiaxiaoxia_rewrite(raw_item):
    """
    将原始情报用虾小侠人格重写
    返回：{title, summary, xiaxiaoxia_comment, link, tags}
    """
    # TODO: 调用 5.2-codex 进行人格化洗稿
    # 当前为骨架代码
    
    return {
        "title": raw_item.get("title", "未命名情报"),
        "summary": raw_item.get("summary", ""),
        "xiaxiaoxia_comment": "[虾小侠短评待生成]",
        "link": raw_item.get("link", ""),
        "tags": raw_item.get("tags", []),
        "source": raw_item.get("source", "unknown")
    }

def process_raw_intelligence():
    """处理所有原始情报数据"""
    today = datetime.now().strftime('%Y-%m-%d')
    raw_files = list(RAW_DIR.glob(f"*{today}*.json"))
    
    if not raw_files:
        print(f"[WARN] 未找到今日 ({today}) 原始数据，跳过处理")
        return None
    
    intelligence_items = []
    
    for raw_file in raw_files:
        print(f"  处理：{raw_file.name}")
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 解析原始数据并洗稿
        items = raw_data.get("items", []) if isinstance(raw_data, dict) else []
        for item in items:
            if item:  # 跳过空数据
                rewritten = xiaxiaoxia_rewrite(item)
                intelligence_items.append(rewritten)
    
    if not intelligence_items:
        print(f"[WARN] 无有效情报项可处理")
        return None
    
    # 产出结构化 JSON
    output = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "persona": "xiaxiaoxia_v1",
        "count": len(intelligence_items),
        "items": intelligence_items
    }
    
    output_file = OUTPUT_DIR / f"intelligence_{today}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 洗稿完成，产出 {len(intelligence_items)} 条情报 → {output_file}")
    return output_file

def main():
    print(f"[{datetime.now()}] 开始虾小侠人格洗稿处理...")
    result = process_raw_intelligence()
    return result is not None

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
