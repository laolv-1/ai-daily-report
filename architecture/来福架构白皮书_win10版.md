# 来福架构白皮书（落盘版）

> 最后更新：2026-03-14 05:25 GMT+8
> 维护责任人：来财
> 节点：来福（阿里云生产中台）
> IP：100.82.179.92
> A2A 端口：18800

---

## ✅ 节点职责
- 爬虫抓取（TikTok / Reddit / GitHub Trending）
- 虾小侠人格洗稿（A 轨情报）
- 藏经阁 full_markdown 清洗
- 闲鱼 / 小红书直销弹药 09:30 定时交付
- /top10_scripts 短视频脚本生成

---

## 📁 目录与脚本（绝对路径）

### 爬虫层
- /root/intelligence_hub/spiders/tiktok_trends.py
- /root/intelligence_hub/spiders/reddit_saas.py
- /root/intelligence_hub/spiders/github_trending.py

### 处理层
- /root/intelligence_hub/processors/xiaxiaoxia_persona.py
- /root/intelligence_hub/processors/markdown_clean.py
- /root/intelligence_hub/processors/laifu_sales_bundle_daily.py

### 定时触发
- /root/intelligence_hub/cron/daily_delivery.py

---

## ⏰ Cron 定时表
- 0 6 * * *  早盘抓取
- 0 7 * * *  虾小侠洗稿
- 0 8 * * *  藏经阁清洗
- 30 9 * * *  直销弹药 + TG 推送
- 0 10 * * *  HK 节点 GitHub Pages 同步

---

## 🔄 数据流向
抓取 → outputs/raw → 洗稿/清洗 → outputs/json & outputs/markdown → C 轨直销 → TG

---

## ⚠️ 铁律
任何新增脚本或 Cron 变更，必须同步更新 US / 来福 / Win10 三端白皮书。

（本文件为 Win10 落地版本）