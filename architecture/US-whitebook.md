# US 主脑白皮书（当前生效版）

> 最后更新：2026-03-15 01:10 GMT+8
> 节点：US 主脑（VPS 生产环境）
> IP：74.48.182.210
> 维护责任人：来财（Laicai）
> 运行环境：2核4G VPS，Node.js v22.22.1，Linux Debian

---

## 🏛️ 一、节点职责

- 总指挥：接收主公指令，拆解任务，分发到来福/HK/Win10 节点
- A2A 网关：通过 port 18800 向来福节点发送任务指令
- OpenClaw 宿主：运行 OpenClaw Agent 主进程（PM2 守护）
- 大屏前端托管：`/root/.openclaw/workspace/ai-daily-report/` 提供 GitHub Pages 数据
- 白皮书仓库：统一存储所有节点的架构白皮书

---

## 🌐 二、8317 网关路由配置

### OpenClaw Gateway 配置（当前生效）

```yaml
# /root/openclaw/config.yaml 关键段

gateway:
  port: 8317
  host: 0.0.0.0
  
  # 路由规则
  routes:
    - path: /api/chat
      handler: chat
      model: lck/claude-sonnet-4-6  # 默认模型
      
    - path: /api/intel
      handler: intel_dispatch
      upstream: lafu_node  # 转发到来福节点
      
    - path: /a2a
      handler: a2a_gateway
      port: 18800

  # A2A 节点配置
  peers:
    lafu_minion:
      ip: 100.82.179.92
      port: 18800
      token: d310cbdb76ae3110415577cffee4382833d321a12e2e32e3
      role: spider_and_llm  # 爬虫 + LLM 清洗节点
      
    win10_relay:
      ip: 100.89.160.67
      port: 3000
      role: browser_relay  # 浏览器自动化节点

  # 安全
  auth:
    require_token: true
    token_header: X-OpenClaw-Token
```

### 防火墙规则（iptables）

```bash
# 允许 OpenClaw Gateway
iptables -A INPUT -p tcp --dport 8317 -j ACCEPT

# 允许 A2A 通信
iptables -A INPUT -p tcp --dport 18800 -j ACCEPT

# 允许 SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 拒绝其他入站
iptables -A INPUT -j DROP

# 保存规则
iptables-save > /etc/iptables/rules.v4
```

---

## 📋 三、PM2 进程清单（当前运行）

```bash
# 查看当前 PM2 状态
pm2 list

# 预期进程表：
┌─────┬──────────────────────────┬──────────┬─────────┬──────────┐
│ ID  │ Name                     │ Status   │ CPU     │ Memory   │
├─────┼──────────────────────────┼──────────┼─────────┼──────────┤
│ 0   │ openclaw-gateway         │ online   │ 0.5%    │ 180MB    │
│ 1   │ a2a-gateway              │ online   │ 0.1%    │ 45MB     │
│ 2   │ intel-dashboard-server   │ online   │ 0.0%    │ 30MB     │
└─────┴──────────────────────────┴──────────┴─────────┴──────────┘

# PM2 常用命令
pm2 status                    # 查看所有进程
pm2 logs openclaw-gateway     # 查看 gateway 日志
pm2 restart all               # 重启所有进程
pm2 save                      # 保存当前进程列表
pm2 startup                   # 开机自启配置
```

### PM2 ecosystem 配置

```javascript
// /root/ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'openclaw-gateway',
      script: '/root/openclaw/dist/gateway/index.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PORT: 8317,
        OPENCLAW_CONFIG: '/root/openclaw/config.yaml'
      }
    },
    {
      name: 'a2a-gateway',
      script: '/root/.openclaw/workspace/plugins/a2a-gateway/skill/server.mjs',
      instances: 1,
      autorestart: true,
      env: {
        A2A_PORT: 18800,
        A2A_TOKEN: 'd310cbdb76ae3110415577cffee4382833d321a12e2e32e3'
      }
    }
  ]
};
```

---

## 🔄 四、跨节点发送命令

### A2A 发送到来福（来财本体使用）

```bash
# 标准发送格式
node /root/.openclaw/workspace/plugins/a2a-gateway/skill/scripts/a2a-send.mjs \
  --peer-url http://100.82.179.92:18800 \
  --token d310cbdb76ae3110415577cffee4382833d321a12e2e32e3 \
  --message "YOUR TASK MESSAGE"

# 示例：触发来福爬虫
node /root/.openclaw/workspace/plugins/a2a-gateway/skill/scripts/a2a-send.mjs \
  --peer-url http://100.82.179.92:18800 \
  --token d310cbdb76ae3110415577cffee4382833d321a12e2e32e3 \
  --message "立刻执行 spider_v3.py，抓取今日情报，门槛55分"
```

### 向 Win10 投递文件（paramiko 静默模式）

```python
# /root/scripts/backup_to_win10.py 核心逻辑
import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('100.89.160.67', username='Administrator', password='As1231')

sftp = client.open_sftp()
sftp.put('/tmp/laicai_backup.tgz', r'D:\来财\白皮书_当前生效版\backup.tgz')
sftp.close()
client.close()
```

---

## ⏰ 五、US 节点 Cron 时间表

```crontab
# US 主脑 Crontab

# 每天 00:00 黄金复活甲备份
0 0 * * * cd /root && python3 /root/scripts/backup_to_win10.py 2>&1 | logger -t laicai-backup

# 每天 09:45 拉取来福最新 JSON 更新大屏
45 9 * * * cd /root && python3 /root/scripts/pull_lafu_intel.py 2>&1

# 每天 23:50 清理 30 天以上的临时日志
50 23 * * * find /root/intelligence_hub/logs -name "*.log" -mtime +30 -delete
```

---

## ⚠️ 六、铁律

1. 严禁使用 `scp` 传文件到 Win10（会弹窗）→ 必须用 paramiko 静默投递
2. PM2 进程崩溃后 autorestart 自动拉起，无需人工干预
3. Gateway 重启前必须先通知主公
4. 所有密码统一读取自 `/root/openclaw/skills/minion_registry.json`，严禁再次向主公索要
