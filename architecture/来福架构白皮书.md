# 来福节点专属架构白皮书（全域情报站 v2.0）

> **最后更新**：2026-03-14 05:25 GMT+8
> **维护责任人**：来财（US 主脑）
> **节点定位**：来福（阿里云生产中台）
> **节点 IP**：100.82.179.92
> **A2A 端口**：18800（双向鉴权）

---

## ✅ 一、节点职责边界（来福专属）
- 24 小时爬虫生产端
- 结构化情报洗稿（虾小侠人格）
- 藏经阁长文清洗（full_markdown）
- 直销弹药每日 09:30 交付（闲鱼 / 小红书）
- 短视频脚本按需生成（/top10_scripts）

---

## 📁 二、物理目录结构（绝对路径）

- `/root/intelligence_hub/`
  - `spiders/` 爬虫脚本
  - `processors/` 数据处理
  - `outputs/raw/` 原始抓取落盘
  - `outputs/json/` A 轨结构化情报
  - `outputs/markdown/` B 轨 full_markdown
  - `outputs/daily_copy/` C 轨直销弹药
  - `outputs/scripts/` D 轨短视频剧本
  - `cron/` 定时任务脚本
  - `logs/` 运行日志

---

## 🧩 三、脚本清单（来福全量）

### 爬虫层（/root/intelligence_hub/spiders）
- `/root/intelligence_hub/spiders/tiktok_trends.py`
- `/root/intelligence_hub/spiders/reddit_saas.py`
- `/root/intelligence_hub/spiders/github_trending.py`
- `/root/intelligence_hub/spiders/xiaohongshu_hot.py`（预留）

### 处理层（/root/intelligence_hub/processors）
- `/root/intelligence_hub/processors/xiaxiaoxia_persona.py`
- `/root/intelligence_hub/processors/markdown_clean.py`
- `/root/intelligence_hub/processors/laifu_sales_bundle_daily.py`
- `/root/intelligence_hub/processors/script_generator.py`（待落地）

### 定时触发（/root/intelligence_hub/cron）
- `/root/intelligence_hub/cron/daily_delivery.py`

---

## ⏰ 四、Cron 定时表（精确）

- `0 6 * * *` 早盘抓取（spiders/*.py）
- `0 7 * * *` 虾小侠洗稿（xiaxiaoxia_persona.py）
- `0 8 * * *` 藏经阁清洗（markdown_clean.py）
- `30 9 * * *` 直销弹药 + TG 推送（laifu_sales_bundle_daily.py）
- `0 10 * * *` HK 节点推送 GitHub Pages（HK 端执行）

---

## 🔄 五、数据流向（来福 → 主公）

1. 爬虫抓取 → `outputs/raw/*.json`
2. 虾小侠洗稿 → `outputs/json/intelligence_YYYY-MM-DD.json`
3. 藏经阁清洗 → `outputs/markdown/library_YYYY-MM-DD.json`（full_markdown）
4. 直销弹药 → `outputs/daily_copy/sales_bundle_YYYY-MM-DD.json` → TG

---

## 📡 六、双向通信端口

- **A2A**：18800（来财 ↔ 来福）
- **TG Bot**：发送通道（见来福环境变量 TG_BOT_TOKEN / TG_CHAT_ID）

---

## ⚠️ 七、铁律

- 任何脚本新增 / Cron 调整，三端白皮书必须同步更新：
  - US 主脑：`/root/.openclaw/workspace/architecture_map.md`
  - 来福节点：`/root/intelligence_hub/architecture_map.md`
  - Win10 落地：`D:\来财\白皮书\来福架构白皮书.md`

---

*此文档为来福节点专属架构底座，主公查岗优先读取*