# 系统变更日志｜2026-03-08

## 今日概况
自动记录本体与蜂群的代码改动、配置修改、新技能固化。

## 新技能固化
- /root/openclaw/skills/skill_context_refresh.md
- /root/openclaw/skills/skill_tool_roi_scheduler.md

## 关键物理文件
- /root/.openclaw/workspace/scripts/soul_backup.py
- /root/.openclaw/workspace/scripts/soul_backup.cron.sh
- /root/.openclaw/workspace/scripts/system_change_log.py
- /root/.openclaw/workspace/scripts/system_change_watchdog.py
- /root/.openclaw/workspace/scripts/cyber_exchange_audit.py
- /root/.openclaw/openclaw.json

## 近期提交
```
641affe Lock approval delivery to BJT windows and add update log
3c02aa1 Add context refresh guardrail
8d54ec3 Fix MolTBook approval pickup timing and silent mode
5e997ae Reformat intel report into dual table layout
9792e19 Fix bot routing for intel vs approval
```

## 当前工作区状态
```
M reports/2026-03-08_update_log.md
 M reports/global-intel-latest.md
?? .openclaw/
?? AGENTS.md
?? BOOTSTRAP.md
?? HEARTBEAT.md
?? IDENTITY.md
?? SOUL.md
?? USER.md
?? memory-lancedb-pro/
?? memory/2026-03-06-2340.md
?? memory/2026-03-06.md
?? memory/2026-03-08.md
?? memory/a2a_heartbeat_cron.log
?? memory/a2a_heartbeat_monitor.log
?? memory/a2a_heartbeat_state.json
?? memory/moltbook_approval_state.json
?? memory/soul_backup.log
?? memory/soul_backup_state.json
?? memory/system_change_log_state.json
?? plugins/
?? reports/approval-outbox/approval-request-20260307-121950.md
?? reports/approval-outbox/approval-request-20260308-000029.md
?? reports/approval-outbox/approval-request-20260308-162646-20260308-000025-broad-scan.draft.md
?? reports/cyber-exchange-last-run.log
?? reports/cyber-exchange/20260306-151428-sandboxing.draft
?? reports/cyber-exchange/20260306-152647-sandboxing.draft
?? reports/cyber-exchange/20260306-180504-sandboxing.draft
?? reports/cyber-exchange/20260306-184959-sandboxing.draft
?? reports/cyber-exchange/20260307-121934-broad-scan.draft
?? reports/cyber-exchange/20260307-121937-broad-scan.draft
?? reports/cyber-exchange/20260307-121940-broad-scan.draft
?? reports/cyber-exchange/20260307-121943-broad-scan.draft
?? reports/cyber-exchange/20260307-121945-broad-scan.draft
?? reports/cyber-exchange/20260307-121948-broad-scan.draft
?? reports/cyber-exchange/20260308-000003-broad-scan.draft
?? reports/cyber-exchange/20260308-000007-broad-scan.draft
?? reports/cyber-exchange/20260308-000012-broad-scan.draft
?? reports/cyber-exchange/20260308-000016-broad-scan.draft
?? reports/cyber-exchange/20260308-000019-broad-scan.draft
?? reports/cyber-exchange/20260308-000025-broad-scan.draft
?? reports/cyber-exchange/cyber-exchange-20260306-151432.md
?? reports/cyber-exchange/cyber-exchange-20260306-152653.md
?? reports/cyber-exchange/cyber-exchange-20260306-180511.md
?? reports/cyber-exchange/cyber-exchange-20260307-000508.md
?? reports/cyber-exchange/cyber-exchange-20260307-060509.md
?? reports/cyber-exchange/cyber-exchange-20260307-120508.md
?? reports/cyber-exchange/cyber-exchange-20260307-121950.md
?? reports/cyber-exchange/cyber-exchange-20260308-000029.md
?? reports/cyber-exchange/http-sandbox-audit.jsonl
?? reports/cyber-exchange/request-audit.jsonl
?? reports/global-intel-20260307-091507.md
?? reports/global-intel-20260307-121956.md
?? reports/global-intel-20260307-122036.md
?? reports/global-intel-20260307-122239.md
?? reports/global-intel-20260307-122429.md
?? reports/global-intel-20260307-123159.md
?? reports/global-intel-20260308-000017.md
?? reports/global-intel-http-audit.jsonl
?? reports/global-intel-last-run.log
?? reports/send-logs/telegram-send-20260307-122429.json
?? reports/send-logs/telegram-send-20260307-123159.json
?? reports/send-logs/telegram-send-20260307-123805.json
?? reports/send-logs/telegram-send-20260308-000017.json
?? scripts/__pycache__/
?? scripts/soul_backup.cron.sh
?? scripts/soul_backup.py
?? scripts/system_change_log.py
?? scripts/system_change_watchdog.cron.sh
?? scripts/system_change_watchdog.py
```

## 本次补充说明
自动巡检发现代码/配置/技能文件发生变化，已生成并推送最新系统变更日志。