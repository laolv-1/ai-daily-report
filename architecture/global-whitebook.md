# 全局架构白皮书（帝国全域总纲）

> 最后更新：2026-03-15 01:10 GMT+8
> 编写人：来财
> 版本：v5.0 正式生效版

---

## 🌐 一、帝国拓扑总图

```
主公 Telegram (7392107275)
      ↑ 战报接收
      │
┌─────┴──────────────────────────────────────────────────────┐
│                    US 主脑 (74.48.182.210)                   │
│  OpenClaw Gateway :8317 │ A2A Server :18800 │ PM2 守护进程  │
└─────────────────────┬──────────────────────────────────────┘
                      │ A2A 指令下发
                      ↓
┌─────────────────────────────────────────────────────────────┐
│               来福中台 (100.82.179.92)                       │
│  spider_v3.py (正文抓取) │ hk_spider.py (藏经阁)            │
│  LLM 清洗 (Input Token 3000+) │ MySQL 数据库                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ 推送 JSON / 文件
                      ↓
┌─────────────────────────────────────────────────────────────┐
│               HK 跳板 (100.119.68.81)                        │
│  GitHub 推送同步 │ 大屏 JSON 分发                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ GitHub API
                      ↓
         GitHub Pages (情报大屏) ──────→ 主公浏览器/Telegram

另:
Win10 机动大本营 (100.89.160.67)
  ├── 黄金备份接收 (D:\来财\白皮书_当前生效版\)
  ├── Browser Relay (OpenClaw Chrome Extension)
  └── ADB 桥接 → 华为手机 (100.71.179.85:5555) → 实弹发布
```

---

## 📊 二、节点规格表

| 节点 | IP | 角色 | 系统 | 核心服务 |
|------|-----|------|------|---------|
| US 主脑 | 74.48.182.210 | 大脑 | Debian Linux | OpenClaw, A2A, PM2 |
| 来福中台 | 100.82.179.92 | 情报工厂 | CentOS | Python 爬虫, MySQL, TG Bot |
| HK 跳板 | 100.119.68.81 | 推送节点 | - | GitHub Actions, Pages |
| Win10 | 100.89.160.67 | 机动大本营 | Windows 10 | Browser Relay, 备份接收 |
| 华为手机 | 100.71.179.85 | 物理分发 | Android | ADB :5555, 实弹发布 |

---

## 🔁 三、数据流全链路

### A 轨：情报流

```
1. 06:00 来福 spider_v3.py 启动
2. 抓取 HN Top Stories + Reddit SaaS → 获取文章 URL
3. newspaper3k 全量抓取正文（3000-10000 chars）
4. 正文 + 标题 → 拼接 Prompt（est. Input Token 3000-8000）
5. 调用 LLM GPT API 深度清洗
6. score < 55 → 丢弃；score ≥ 55 → 写入 outputs/json/
7. 07:00 daily_harvest_pipeline.py 合并所有 JSON
8. 10:00 推送到 GitHub Pages daily_intel.json
9. 前端 Tab 过滤（filterCards by data-category）
10. TG Bot 推送今日情报摘要给主公
```

### B 轨：藏经阁流

```
1. 08:00 hk_spider.py 启动
2. 抓取 DigitalOcean / Linux Journey / Docker Docs
3. BeautifulSoup 提取全量技术正文
4. 打标 tab_category = "藏经阁"，score = 75
5. 写入 hk_spider_output.json
6. 合并至 daily_intel.json
7. 大屏【藏经阁】Tab 展示
```

### C 轨：直销弹药流

```
1. 09:30 laifu_sales_bundle_daily.py 启动
2. 读取今日情报中 "搞钱" / "变现" 标签条目
3. 生成闲鱼/小红书直销文案
4. TG Bot 推送给主公
5. ADB → 华为手机 → 发帖（实弹）
```

---

## 🤖 四、TG Bot 配置

```python
# 来福 TG Bot
BOT_TOKEN = "8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0"
MASTER_CHAT_ID = 7392107275  # 主公接收 ID

# 推送示例
import requests
def send_to_master(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": MASTER_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()
```

---

## 🛡️ 五、铁律（全节点通用）

1. **凭证自理**：所有密码从 `/root/openclaw/skills/minion_registry.json` 读取，禁止再向主公索要
2. **Win10 文件投递**：一律使用 paramiko 静默模式，禁止使用 scp（会触发弹窗）
3. **Token 消耗红线**：每次 LLM 调用 Input Token 必须 > 3000（确保正文全量注入）
4. **分数门槛**：暂时 55 分，待数据稳定后调回 70 分
5. **反静默定律**：超过 30 秒的任务必须先发心跳告知主公
6. **8次熔断**：单轮 Tool Call 达 8 次进入冷却，先落盘再继续
7. **黄金备份**：每天 00:00 打包技能和白皮书，物理投递到 Win10 `D:\来财\`
8. **Mermaid 节点命名**：全部用英文下划线命名（US_Node, LF_Node），文字用 `["..."]` 包裹

---

## 📅 六、全局 Cron 时间表汇总

| 时间 | 节点 | 任务 |
|------|------|------|
| 06:00 | 来福 | spider_v3.py A轨情报抓取 |
| 07:00 | 来福 | LLM 清洗 + 输出 JSON |
| 08:00 | 来福 | hk_spider.py 藏经阁抓取 |
| 09:30 | 来福 | 直销弹药生成 + TG 推送 |
| 09:45 | US | 拉取来福最新 JSON 更新大屏 |
| 10:00 | 来福/HK | GitHub Pages 大屏同步 |
| 00:00 | US | 黄金备份打包投递 Win10 |
| 23:50 | US | 清理 30 天以上临时日志 |
