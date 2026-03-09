# skill_tg_broadcast_assistant

## 适用场景

用于在**自有社群、授权频道、白名单群组**上部署 Telegram 合规广播助手。禁止用于扫描未授权群组、批量骚扰、广告滥发或任何规避风控行为。

## 核心目标

- 用 `Telethon` 搭建双客户端结构：
  - **Bot 控制端**：接收管理员指令
  - **User 操作端**：只向白名单群组发公告
- 所有目标群必须来自 `whitelist_groups`
- 每发一个群必须严格 `asyncio.sleep(interval_minutes * 60)`
- 完成一轮后再休眠，避免高频刷屏
- 运行前必须先通过 `login.py` 生成合法 `.session`

## 文件布局

放在目标机目录（例如 `/root/hk_tg_broadcast`）：

- `hk_tg_broadcast_bot.py`
- `login.py`
- `config.json`
- `broadcast.log`
- `bot_control.session`
- `user_operator.session`

## config.json 关键字段

- `api_id`
- `api_hash`
- `bot_token`
- `admin_ids`
- `announcement_msg`
- `interval_minutes`
- `whitelist_groups`
- `is_running`

## 管理指令

- `/msg 内容`：设置公告
- `/targets 群ID1 群ID2 ...`：设置白名单
- `/time 分钟`：设置群间隔
- `/start`：开始广播
- `/stop`：停止广播
- `/status`：查看状态和最近审计

## 合规限制

- 不扫描“已加入的全部群”
- 不自动发现陌生目标
- 仅允许 `admin_ids` 中的管理员下发命令
- 白名单为空时拒绝启动
- 公告为空时拒绝启动
- 发生 `FloodWait` 时必须暂停并记录审计

## 登录步骤

1. 先在目标机安装 `python3-pip` 与 `telethon`
2. 执行：`cd /root/hk_tg_broadcast && python3 login.py`
3. 按提示输入手机号、验证码（如启用二步验证还需输入密码）
4. 确认生成 `user_operator.session`
5. 再用 PM2 守护主脚本

## PM2 启动

推荐：

```bash
cd /root/hk_tg_broadcast
pm2 start hk_tg_broadcast_bot.py --name TG-Broadcast-Assistant --interpreter python3
pm2 save
```

## 排障要点

- 若 `python3 -m pip` 不存在：先补 `python3-pip`
- 若 `ModuleNotFoundError: telethon`：重新执行 `python3 -m pip install telethon`
- 若主脚本报未授权：说明 `user_operator.session` 尚未生成，先跑 `login.py`
- 若消息无法发出：检查 `whitelist_groups` 是否可达、账号是否仍在群内、是否命中 Telegram 限流

## 可复用骨架

双客户端主结构：

1. `bot_client.start(bot_token=...)`
2. `user_client.connect()`
3. `if not await user_client.is_user_authorized(): raise RuntimeError(...)`
4. `@bot_client.on(events.NewMessage(...))` 处理管理员指令
5. `asyncio.create_task(broadcaster_loop(...))`
6. `broadcaster_loop()` 中只对白名单逐个发送，并在每个群之间严格休眠

## 资产原则

这是一个**合规广播自动化资产**，重点是白名单、审计、低频、可停机，不是群发器，不是攻击工具。
