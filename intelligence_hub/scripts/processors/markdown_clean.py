#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
藏经阁 full_markdown 清洗处理器 (B 轨核心)
输入：/root/intelligence_hub/outputs/raw/github_trending_YYYY-MM-DD.json
产出：/root/intelligence_hub/outputs/markdown/library_YYYY-MM-DD.json
"""

import json
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("/root/intelligence_hub/outputs/raw")
OUTPUT_DIR = Path("/root/intelligence_hub/outputs/markdown")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_to_full_markdown(raw_item):
    """
    将抓取的项目文档/README/教程转为 full_markdown
    TODO: 接入 gpt-5.2-codex 深度清洗
    """
    return {
        "title": raw_item.get("title", "未命名项目"),
        "source_url": raw_item.get("link", ""),
        "full_markdown": raw_item.get("full_markdown", "[待生成]"),
        "tags": raw_item.get("tags", []),
        "summary": raw_item.get("summary", "")
    }


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    raw_file = RAW_DIR / f"github_trending_{today}.json"
    if not raw_file.exists():
        print(f"[WARN] 未找到 {raw_file}，跳过")
        return False

    with open(raw_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    items = []
    for block in raw_data:
        items.extend(block.get("items", []))

    cleaned = [clean_to_full_markdown(i) for i in items]
    output = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "count": len(cleaned),
        "items": cleaned
    }

    output_file = OUTPUT_DIR / f"library_{today}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] 藏经阁清洗完成：{output_file}")
    return True


if __name__ == '__main__':
    main()
