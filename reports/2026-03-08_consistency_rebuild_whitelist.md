# 分布式情报节点一致性重构白名单（2026-03-08）

## 一、执行原则

- 先审计，后迁移，再下线，最后物理清除。
- 任何当前仍被 cron / PM2 / A2A / 业务流程直接引用的产物，禁止先删。
- 本文件作为后续“大清洗”的唯一手术单。

## 二、本体（VPS）

| 分类 | 路径/对象 | 当前状态 | 处理动作 |
|---|---|---:|---|
| 保留 | `/root/.openclaw/workspace/scripts/global_intel_dispatch.py` | 现役 | 保留，后续改造成“仅调度/不留生肉” |
| 保留 | `/root/.openclaw/workspace/scripts/pull_and_push_intel.py` | 现役 | 保留，后续可能并入来福主编总控 |
| 保留 | `/root/.openclaw/workspace/scripts/cyber_exchange_audit.py` | 现役 | 保留 |
| 保留 | `/root/.openclaw/workspace/scripts/market_research_daily.py` | 现役 | 保留，后续改造成来福主编发送 |
| 保留 | `/root/.openclaw/workspace/scripts/a2a_heartbeat_monitor.py` | 现役 | 保留 |
| 保留 | `/root/.openclaw/workspace/scripts/context_refresh_guard.py` | 现役 | 保留 |
| 保留 | `/root/.openclaw/workspace/scripts/soul_backup.py` | 现役 | 保留 |
| 保留 | `/root/.openclaw/workspace/scripts/system_change_log.py` | 现役 | 保留 |
| 保留 | `/root/.openclaw/workspace/scripts/system_change_watchdog.py` | 现役 | 保留 |
| 待迁移 | `/root/.openclaw/workspace/reports/global-intel-*.md` | 历史产物堆积 | 迁移归档后再清理旧批次 |
| 待迁移 | `/root/.openclaw/workspace/reports/send-logs/telegram-send-*.json` | 历史发送回执 | 保留最近窗口，其余归档 |
| 待迁移 | `/root/.openclaw/workspace/reports/cyber-exchange/*.draft` | 历史草稿镜像 | 迁移归档后清理 |
| 待迁移 | `/root/.openclaw/workspace/reports/approval-outbox/*.md` | 历史审批单 | 仅保留最近必要窗口，其余归档 |
| 待审计 | `/root/.openclaw/workspace/scripts/polymarket_phantom_hunt.py` | 与当前情报主线弱相关 | 单独评估是否脱离主系统 |

## 三、来福（100.82.179.92）

| 分类 | 路径/对象 | 当前状态 | 处理动作 |
|---|---|---:|---|
| 保留 | `/opt/intel_spider/spider_v3.py` | 现役 cron 抓取 | 保留，后续重构源阵列 |
| 保留 | `/opt/intel_spider/push_v3.py` | 现役 cron 推送 | 保留，后续重构为主编总控输出 |
| 保留 | `/var/log/intel_spider_v3.log` | 现役日志 | 保留最近窗口 |
| 保留 | `/var/log/intel_push_v3.log` | 现役日志 | 保留最近窗口 |
| 冗余候选 | `/opt/intel_spider/spider.py` | 旧版本 | 确认未被引用后清理 |
| 冗余候选 | `/opt/intel_spider/spider_v2.py` | 旧版本 | 确认未被引用后清理 |
| 冗余候选 | `/opt/intel_spider/top3_v2.py` | 旧版本 | 确认未被引用后清理 |
| 冗余候选 | `/opt/intel_spider/top3_report.py` | 辅助旧版本 | 确认未被引用后清理 |
| 冗余候选 | `/var/log/intel_spider.log` | 旧日志 | 归档后清理 |
| 冗余候选 | `/var/log/intel_spider_v2.log` | 旧日志 | 归档后清理 |
| 冗余候选 | `/var/log/intel_top3.log` | 旧日志 | 归档后清理 |
| 待新增 | `intel_station.raw_signals`（建议新表） | 尚未建立 | 用于全域 raw signal 单向汇流 |
| 待新增 | `intel_station.editorial_outputs`（建议新表） | 尚未建立 | 用于主编清洗/脚本工厂产物 |

## 四、HK（100.119.68.81）

| 分类 | 路径/对象 | 当前状态 | 处理动作 |
|---|---|---:|---|
| 保留 | `/root/openclaw-node` | 现役 OpenClaw 运行时 | 保留 |
| 保留 | `/root/openclaw-hk-workspace/plugins/a2a-gateway` | 现役 A2A 插件 | 保留 |
| 保留 | `/www/wwwroot/b.apiepay.cn/*.php` | 现役业务入口 | 仅审计，不做业务逻辑改造 |
| 保留 | `/www/wwwroot/h5.yunapi.cyou/*.php` | 现役业务入口 | 仅审计，不做业务逻辑改造 |
| 待审计 | `/www/server/cron/*` 对应 5 条 cron | 宝塔侧现役未知 | 逐条反查脚本内容，再决定保留/下线 |
| 待清理确认 | HK 历史传输残留 `.tgz` | 已清除 | 保持空态 |

## 五、当前统一时序约束

| 任务 | 责任节点 | 时间 | 当前状态 | 目标状态 |
|---|---|---|---|---|
| MolTBook 审批 | 来财 | `12:00 / 00:00` BJT | 已锁窗 | 继续保持 |
| ClawWork 调研 | 当前由本体脚本执行，使用来福 Bot 发送 | `12:30` BJT | 发送身份已对齐，执行身份未对齐 | 重构为来福主编节点自主出稿 |
| 国内情报抓取 | 来福 | 每 30 分钟 | 现役 | 未来替换低信号源 |
| 国内情报推送 | 来福 | `09:00 / 21:00` BJT | 现役 | 未来并入主编总控 |

## 六、下一步重构顺序

1. 反查 HK 宝塔 5 条 cron 的真实脚本内容。
2. 在来福 MySQL 设计并创建统一汇流表：`raw_signals`、`editorial_outputs`。
3. 把本体海外抓取改造成“提取后即写来福，不保留本地业务镜像”。
4. 把 `market_research_daily.py` 的执行责任迁到来福，满足“12:30 调研由来福发送”。
5. 迁移归档本体与来福历史产物，再按白名单物理清理旧脚本/旧日志。

## 七、当前明确未完成/卡点

- 海外高频多媒体源（YT/X）尚未接入，当前仍是 Reddit/公开源为主。
- 来福“主编语义工厂”尚未正式接入专用清洗算力。
- “15-30 秒交互文案工厂”仅有规划，未形成自动闭环。
- HK 的宝塔 cron 仍是审计盲区。
- 本体当前仍保留历史业务报表与发送回执，尚未切到“阅后即焚”架构。
