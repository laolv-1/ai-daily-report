# 系统变更日志｜2026-03-08

## 一、今日新增功能

### 1. 五核工具优先调度技能
- 新增技能文件：`/root/openclaw/skills/skill_tool_roi_scheduler.md`
- 新固化逻辑：优先使用高 ROI 的五类工具（读、改、跑、跨网、发），减少低价值工具挤占上下文。
- 关键收益：降低工具定义开销、减少无效调用、抑制长会话降智。

### 2. 上下文强制刷新护城河
- 新增技能文件：`/root/openclaw/skills/skill_context_refresh.md`
- 新增脚本：`/root/.openclaw/workspace/scripts/context_refresh_guard.py`
- 新增 cron 包装：`/root/.openclaw/workspace/scripts/context_refresh_guard.cron.sh`
- 新固化逻辑：8 次 Tool Call 警戒、重任务前落盘断点、定期清扫旧 session / 报表 / 大日志。

## 二、今日修改逻辑

### 1. MolTBook 审批时间死锁
- 修改文件：`/root/.openclaw/workspace/scripts/cyber_exchange_audit.py`
- 修改点：新增 `enforce_bjt_delivery_window()`
- 新逻辑：
  - 只有北京时间 `00:00` 与 `12:00` 允许 Telegram 审批发送
  - 其他任何时间即便脚本被手动误触，也会 `SystemExit(0)` 静默退出
- 配合机制：crontab 已使用 `CRON_TZ=Asia/Shanghai` + `0 0,12 * * *`

### 2. MolTBook 跨网取件逻辑
- 修改文件：`/root/.openclaw/workspace/scripts/cyber_exchange_audit.py`
- 修改点：审批单来源从“本机幻想路径”修正为“VPS paramiko 跨网连接阿里云 `/www/wwwroot/spider_center/molt_learning/` 取 `.draft`”
- 新逻辑：无新件 / 低价值件一律静默，不向主公输出调试噪音。

## 三、当前定时任务基线

```cron
CRON_TZ=Asia/Shanghai
*/5 * * * * /usr/bin/python3 /root/.openclaw/workspace/scripts/a2a_heartbeat_monitor.py >> /root/.openclaw/workspace/memory/a2a_heartbeat_cron.log 2>&1
0 0,12 * * * /root/.openclaw/workspace/scripts/cyber_exchange_audit.cron.sh
0 0,12 * * * /root/.openclaw/workspace/scripts/pull_and_push_intel.cron.sh
15 */6 * * * /root/.openclaw/workspace/scripts/context_refresh_guard.cron.sh
```

## 四、结论
- 今日已完成：工具调度护城河固化、上下文防降智固化、MolTBook 审批时间死锁固化。
- 当前审批链路规则：只有北京时间 12:00 / 24:00 允许发 Telegram，其他时间绝对静默。
