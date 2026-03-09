# skill_win10_automation_v2.md

## 适用场景

当主公要求在 Win10 节点上打通以下链路时使用：

- OpenClaw Gateway 官方配置对齐与转绿
- 通过 SSH / 计划任务击穿 Windows 会话隔离
- 使用 Chrome 原生 `--remote-debugging-port` + `connect_over_cdp` 接管现有 Windows Chrome
- 验收 YouTube 等真实网页标题抓取

本技能基于一次真实实战沉淀，目标机器：

- Win10 节点：`100.89.160.67`
- 用户：`Administrator`
- OpenClaw CLI 版本：`2026.3.8 (3caab92)`

---

## 一、2026.3.8 Gateway 官方配置标准

### 1. 关键结论

Win10 本机 `openclaw gateway --help` 已证实：

- `--bind <mode>` 只接受：
  - `loopback`
  - `lan`
  - `tailnet`
  - `auto`
  - `custom`

因此：

- 旧式 `127.0.0.1` 写法不是该版本的合法 `gateway.bind`
- `gateway.dangerouslyDisableDeviceAuth` 对该版本属于未知键
- Gateway 采用严格 schema 校验，未知键会直接阻止服务启动

### 2. Win10 最小可用基线配置

`C:\Users\Administrator\.openclaw\openclaw.json`

```json
{
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "port": 18789
  }
}
```

### 3. 官方修复链

优先顺序：

```bat
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" doctor --fix --non-interactive
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" gateway stop
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" gateway start
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" gateway status
```

### 4. 验收标准

必须看到：

- `RPC probe: ok`
- `Listening: 127.0.0.1:18789`

如果没有这两条，不准报绿。

---

## 二、Windows 会话隔离与 9222 点火判因

### 1. 真实现象

早期在 SSH/服务上下文中直接拉起：

```bat
chrome.exe --profile-directory="Profile 2" --remote-debugging-port=9222
```

会出现：

- Chrome 进程存在
- 但 `9222` 在连续 10~15 秒内始终不监听
- `connect_over_cdp('http://127.0.0.1:9222')` 拒连 / 超时

### 2. 会话证据

通过：

```bat
query user
qwinsta
```

可确认：

- `Administrator` 处于 `console / Session 1 / 运行中`
- 系统同时存在 `services / Session 0`

这说明远程/服务触发的 GUI 程序，可能并未真正附着到桌面交互会话。

### 3. 最终排除法结论

真正把 9222 点亮的不是 `Profile 2`，而是：

- 保留计划任务 `/it`
- 改用全新的物理用户目录

即：

```bat
--remote-debugging-port=9222 --user-data-dir="C:\Users\Administrator\cdp_tmp_test"
```

### 4. 死因判词

如果临时目录能点亮 9222，而 `Profile 2` 不能，说明：

> 不是系统彻底封杀 remote-debugging；真正的死因是 `Profile 2` 现有用户态/残留实例/接管链导致参数失效或被复用吞掉。

这次实战已拿到该结论。

---

## 三、跨会话点火推荐方案（Windows 原生）

### 1. 批处理点火器

`C:\Users\Administrator\launch_chrome_cdp_tmp.bat`

```bat
@echo off
set LOG=C:\Users\Administrator\cdp_tmp_launch.log
echo ==== %date% %time% ====>> "%LOG%"
echo kill all chrome>> "%LOG%"
taskkill /F /IM chrome.exe /T >> "%LOG%" 2>&1
ping 127.0.0.1 -n 3 >nul
if exist C:\Users\Administrator\cdp_tmp_test rmdir /s /q C:\Users\Administrator\cdp_tmp_test >> "%LOG%" 2>&1
mkdir C:\Users\Administrator\cdp_tmp_test >> "%LOG%" 2>&1
echo launch tmp profile chrome>> "%LOG%"
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\Administrator\cdp_tmp_test" --no-first-run --no-default-browser-check about:blank
ping 127.0.0.1 -n 10 >nul
echo netstat>> "%LOG%"
netstat -ano >> "%LOG%" 2>&1
echo tasklist>> "%LOG%"
tasklist /v >> "%LOG%" 2>&1
```

### 2. 计划任务创建

```bat
schtasks /create /tn OpenClawCDPTmp /sc ONCE /st 23:59 /ru Administrator /rp As1231 /rl HIGHEST /it /tr "C:\Users\Administrator\launch_chrome_cdp_tmp.bat" /f
```

### 3. 立刻触发

```bat
schtasks /run /tn OpenClawCDPTmp
```

### 4. 查看最近运行状态

```bat
schtasks /query /tn OpenClawCDPTmp /fo LIST /v
```

重点看：

- `状态`
- `上次运行时间`
- `上次结果`
- `登录状态`

> 注意：不要只看“尝试运行”，要反查 `schtasks /query /v` 的实际状态。

---

## 四、9222 嗅探脚本

`C:\Users\Administrator\probe_9222.bat`

```bat
@echo off
for /L %%i in (1,1,15) do (
  echo TICK_%%i
  curl http://127.0.0.1:9222/json/version
  netstat -ano | findstr :9222
  ping 127.0.0.1 -n 2 >nul
)
```

### 成功标志

看到以下任一即视为 9222 已点亮：

- `/json/version` 返回 JSON
- `netstat` 出现 `127.0.0.1:9222 LISTENING`
- 返回 `webSocketDebuggerUrl`

---

## 五、CDP 接管与网页标题验收

### 1. Python 接管脚本

`C:\Users\Administrator\cdp_youtube_title.py`

```python
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    if browser.contexts:
        ctx = browser.contexts[0]
    else:
        raise RuntimeError('NO_CONTEXT')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=60000)
    time.sleep(6)
    print('TITLE=' + page.title())
    browser.close()
```

### 2. 本次实战真实验收结果

真实回执：

```text
TITLE=YouTube
```

这就是 CDP 接管成功的最终胜利凭证。

---

## 六、实战判词与后续策略

### 已确认成立

- Gateway 问题已经解决，基线配置固定为：
  - `mode=local`
  - `bind=loopback`
  - `port=18789`
- Windows 跨会话可以通过 `schtasks /it` 打入交互链
- 临时用户目录可成功点亮 `9222`
- `connect_over_cdp` 可接管并抓到 YouTube 标题

### 当前最终死因

`Profile 2` 链路失败的核心原因更像是：

- 用户态残留实例
- 旧 profile 复用/接管
- 参数被已有 Chrome 会话吞掉

而不是：

- OpenClaw 不支持
- Windows 完全封死 9222
- Playwright / CDP 本身失效

### 后续若一定要接管 `Profile 2`

建议排查顺序：

1. 彻底清理全部 `chrome.exe`
2. 检查是否仍有后台残留进程
3. 必要时重启 Win10
4. 再以计划任务 `/it` 方式重新点 `Profile 2`
5. 若仍失败，则继续优先用临时目录法保通，再单独做 Profile 清障

---

## 七、执行层避坑

### 1. 不要再用超长 PowerShell 复合命令

已实证高危：

- `&` 易触发 PowerShell 解析报错
- `>nul` 也可能被外层 PowerShell 污染
- Paramiko 长串 here-string / `&` / 复合管道极不稳定

### 2. 更稳的做法

- **SFTP 直写文件**
- **短 bat / py 文件落地执行**
- 每次只执行一个明确命令

### 3. Telegram/战报口径

未看到：

- `RPC probe: ok`
- `127.0.0.1:9222 LISTENING`
- `TITLE=...`

之前，绝不准谎报成功。
