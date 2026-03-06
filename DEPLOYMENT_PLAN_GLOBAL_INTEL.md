# 全球情报与国内社交抓取整合部署计划

## 一、双擎拓扑

### 1. 国内情报矿场（阿里云）
职责：
- 继续运行国内情报抓取脚本
- 将结果写入 MySQL `intel_station.intel_articles`
- 不再直接连接 Telegram

当前已确认资产：
- 主机：`100.82.179.92`
- 抓取目录：`/opt/intel_spider`
- 关键脚本：`spider.py` / `spider_v2.py` / `spider_v3.py` / `push_v3.py`
- 关键表：`intel_station.intel_articles`

### 2. 海外情报与总控分发（VPS）
职责：
- 抓 Reddit 海外高信号帖子
- 通过 SSH 到阿里云提取国内情报
- 融合国内外情报并调用模型生成日报
- 统一通过 Telegram 发给主人
- 挂本地 crontab 定时执行

当前已落地脚本：
- `scripts/global_intel_dispatch.py`
- `scripts/global_intel_dispatch.cron.sh`

## 二、数据流
1. 阿里云抓国内情报 -> MySQL
2. VPS 抓 Reddit -> 本地筛噪
3. VPS SSH 提货阿里云 MySQL -> 拉回国内 Top 情报
4. VPS 调用模型 -> 生成《全球双擎情报日报》
5. VPS 统一推送 Telegram

## 三、筛选策略

### Reddit 侧
重点社区：
- `r/SaaS`
- `r/Stripe`
- `r/cybersecurity`

保留高信号关键词：
- ban / fraud / chargeback / suspend / compliance / breach / exploit / outage / vulnerability / security / payment

降权垃圾内容：
- meme / shitpost / weekly thread / hiring / funny / off topic

### 国内侧
按以下字段排序：
- `anxiety_score DESC`
- `published_at / created_at DESC`

## 四、后续增强
1. 把阿里云侧 `source` 进一步拆成微信 / V2EX / 微博 / IT之家 / 论坛等来源维度
2. 给 Reddit 增加去重、黑名单和白名单规则
3. 给日报增加“领导摘要版 / 风控执行版 / 安全排查版”三种输出
4. 给总控脚本增加推送成功后写回 `push_status`
5. 给 Telegram 推送增加失败重试与本地归档

## 五、当前实盘状态
- Tailscale 已打通
- Win10 SSH / SMB 已打通
- 阿里云 SSH 已打通
- 国内情报库结构已摸清
- VPS 海外抓取 + 模型总结 + 本地出报已跑通
- 下一步已进入 Telegram 统一发射与定时化运行
