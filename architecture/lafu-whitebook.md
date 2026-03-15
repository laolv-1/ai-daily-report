# 来福节点白皮书（当前生效版）

> 最后更新：2026-03-15 01:10 GMT+8
> 节点：来福（阿里云生产中台）
> IP：100.82.179.92
> Root 密码：8ce42842#
> MySQL 密码：7c8a1c78902e5035
> 维护责任人：来财

---

## 🗺️ 一、节点职责

- A 轨情报爬虫：抓取海内外真实源 URL，提取全量正文（newspaper3k + BS4）
- B 轨藏经阁：Docker / Linux / AI 长篇技术教程抓取与清洗
- LLM 清洗：正文拼入 Prompt，估算 Input Token 3000+ 喂给 GPT 模型
- 定时任务：PM2 + Crontab 双保险调度
- TG Bot 推送：通过 laifu_tg_bot.py 向主公发战报

---

## 📁 二、目录结构（绝对路径）

```
/root/intelligence_hub/
├── spiders/
│   ├── spider_v3.py          # A轨：正文深度抓取引擎（newspaper3k + BS4）
│   └── hk_spider.py          # B轨：藏经阁技术长文抓取引擎
├── processors/
│   ├── laifu_sales_bundle_daily.py   # 直销弹药生成
│   └── markdown_clean.py             # 藏经阁 Markdown 清洗
├── cron/
│   └── daily_delivery.py    # 定时调度入口
├── outputs/
│   ├── json/
│   │   ├── spider_v3_output.json    # A轨最新输出
│   │   └── hk_spider_output.json   # B轨最新输出
│   ├── markdown/                    # 藏经阁 Markdown 文件
│   └── daily_copy/                  # 直销弹药文案
└── logs/                            # 运行日志
    └── daily_harvest_YYYY-MM-DD.log

/root/laifu_tg_bot.py       # TG Bot 推送主程序
/root/daily_harvest_pipeline.py  # 旧版主流程（保留兼容）
```

---

## 🌐 三、真实源 URL 清单（A 轨情报）

### 国际源
| 名称 | URL | 类型 | 优先级 |
|------|-----|------|--------|
| Hacker News Top | https://hacker-news.firebaseio.com/v0/topstories.json | JSON API | ★★★★★ |
| HN Item | https://hacker-news.firebaseio.com/v0/item/{id}.json | JSON API | ★★★★★ |
| Reddit SaaS | https://www.reddit.com/r/SaaS/top.json?limit=5&t=day | JSON API | ★★★★ |
| Reddit Entrepreneur | https://www.reddit.com/r/Entrepreneur/top.json?limit=5&t=day | JSON API | ★★★★ |
| GitHub Trending | https://github.com/trending | HTML 爬取 | ★★★★ |
| CoinGecko | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=10 | JSON API | ★★★ |

### 藏经阁技术源（B 轨）
| 名称 | URL | 标签 |
|------|-----|------|
| DigitalOcean Docker Tutorial | https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-22-04 | Docker,Linux |
| Linux Journey | https://linuxjourney.com/lesson/the-shell | Linux,基础 |
| Docker Docs Get Started | https://docs.docker.com/get-started/ | Docker |
| GitHub Docs | https://docs.github.com/en/get-started | Git,GitHub |
| Cline GitHub | https://github.com/cline/cline | AI,Cursor |

---

## ⏰ 四、Cron 定时表（当前生效）

```crontab
# 来福节点 Crontab - 最后更新 2026-03-15
# crontab -e 查看/修改

# 早盘抓取：06:00 - A轨情报爬虫
0 6 * * * cd /root && python3 /root/intelligence_hub/spiders/spider_v3.py >> /root/intelligence_hub/logs/spider_v3_$(date +\%Y-\%m-\%d).log 2>&1

# 洗稿处理：07:00 - LLM 清洗情报
0 7 * * * cd /root && python3 /root/daily_harvest_pipeline.py >> /root/intelligence_hub/logs/harvest_$(date +\%Y-\%m-\%d).log 2>&1

# 藏经阁抓取：08:00 - B轨技术文章
0 8 * * * cd /root && python3 /root/intelligence_hub/spiders/hk_spider.py >> /root/intelligence_hub/logs/hk_spider_$(date +\%Y-\%m-\%d).log 2>&1

# 直销弹药：09:30 - 生成 + TG 推送
30 9 * * * cd /root && python3 /root/intelligence_hub/processors/laifu_sales_bundle_daily.py >> /root/intelligence_hub/logs/sales_$(date +\%Y-\%m-\%d).log 2>&1

# GitHub Pages 同步：10:00 - 推送大屏 JSON
0 10 * * * cd /root && python3 /root/intelligence_hub/cron/daily_delivery.py >> /root/intelligence_hub/logs/delivery_$(date +\%Y-\%m-\%d).log 2>&1

# 黄金备份：00:00 - 当日技能打包备份到 Win10
0 0 * * * cd /root && tar czf /tmp/laicai_backup_$(date +\%Y-\%m-\%d).tgz /root/intelligence_hub/ && python3 /root/scripts/backup_to_win10.py 2>&1
```

---

## 🔄 五、数据流向

```
抓取层 (spider_v3.py / hk_spider.py)
    ↓ 全量正文 (3000-10000 chars)
LLM 清洗 (Prompt = 标题 + 全文 → GPT 洗稿)
    ↓ 结构化 JSON (score ≥ 55 上墙)
outputs/json/*.json
    ↓ 合并
daily_intel.json (17KB+)
    ↓ 推送
GitHub Pages 大屏 (动态 Tab 过滤)
    ↓ TG Bot 摘要推送
主公 Telegram
```

---

## 🛡️ 六、排障指南

```bash
# 查看最新爬虫日志
tail -50 /root/intelligence_hub/logs/spider_v3_$(date +%Y-%m-%d).log

# 手动触发爬虫测试
python3 /root/intelligence_hub/spiders/spider_v3.py

# 查看 TG Bot 状态
ps aux | grep laifu_tg_bot

# 查看 Cron 状态
crontab -l
service crond status
```

---

## ⚠️ 铁律

1. 任何新增脚本必须同步更新本白皮书
2. API Key 禁止硬编码到代码，必须用环境变量
3. 爬虫 Input Token 门槛：每次 LLM 调用必须 > 3000 tokens
4. 上墙分数线：暂时设为 55 分（待主公调整）
5. 来福 → US 汇报通道：A2A Gateway port 18800
