# skill_win10_automation_v2.md

## 适用场景

当主公要求在 Win10 节点上打通以下链路时使用：

- OpenClaw Gateway 官方配置对齐与转绿
- 通过 SSH / 计划任务击穿 Windows 会话隔离
- 使用 Chrome 原生 `--remote-debugging-port` + `connect_over_cdp` 接管现有 Windows Chrome
- 使用 **OpenClaw Chrome Extension Relay** 接管 Win10 真实 Chrome 标签页
- 评估并扩展到 Win10 本地桌面软件控制（IDE / 记事本 / OpenCode / Codex 等）
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

## 六、官方插件接管法（Chrome Extension Relay）

### 2026-03-10 实战胜利回执（Win10 Profile 2 真身）

- 主公手动完成扩展加载、Options 填入 Gateway Token、目标标签页点击扩展，最终徽标为 **ON**
- Win10 本机官方 CLI 真实回执：
  - `openclaw browser --browser-profile chrome tabs`
  - 返回：
    - `1. YouTube`
    - `https://www.youtube.com/`
    - `id: 94109D4A37A7D801CD4DEAF4564AA4FE`
- Win10 本机官方 CLI `snapshot` 成功抓到 YouTube 页面结构树
- 因此后续 Win10 浏览器接管唯一标准 SOP 固化为：
  1. 保持 Win10 本机 Gateway 正常：`RPC probe: ok`
  2. 扩展 Options 正确填写 `gateway.auth.token`
  3. 在 `Profile 2` 目标标签页点击扩展至 **ON**
  4. 统一使用：`openclaw browser --browser-profile chrome ...`
- 结论：**停止继续折腾裸 9222；Win10 浏览器标准主路正式切换为官方 Chrome Extension Relay。**


### 1. 定位

当目标是接管 **Win10 上主公真实账号正在使用的 Chrome 标签页** 时，优先使用官方插件法，而不是继续死磕裸 `9222`。

官方文档已确认：

- OpenClaw 内建浏览器 profile：`chrome`
- 扩展链路由三部分组成：
  - Browser control service
  - Local relay server（默认 `http://127.0.0.1:18792`）
  - Chrome MV3 extension（通过 `chrome.debugger` 附着当前 tab）
- 当 Gateway 不在浏览器本机时，官方推荐在浏览器所在机器运行 **node host** 作为代理

### 2. Win10 已确认的真实物理回执

在 Win10 `100.89.160.67` 上已实跑：

```bat
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" browser extension install
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" browser extension path
```

真实回执：

```text
~\.openclaw\browser\chrome-extension
Copied to clipboard.
Next:
- Chrome → chrome://extensions → enable “Developer mode”
- “Load unpacked” → select: ~\.openclaw\browser\chrome-extension
- Pin “OpenClaw Browser Relay”, then click it on the tab (badge shows ON)
```

### 3. 标准 SOP

#### Win10 本机准备

1. 执行：

```bat
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" browser extension install
"C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" browser extension path
```

2. 在 Chrome 打开：

```text
chrome://extensions
```

3. 打开 **Developer mode**
4. 点击 **Load unpacked**
5. 选择：

```text
C:\Users\Administrator\.openclaw\browser\chrome-extension
```

6. Pin 扩展到工具栏

#### 主公首次 Attach

1. 用 **Profile 2** 打开目标真实标签页
2. 点击工具栏里的 **OpenClaw Browser Relay**
3. 若 badge 显示 `ON`，表示该标签页已附着
4. 后续主脑通过：
   - `browser profile="chrome"`
   - 同一标签页 targetId
   进行标准控制

### 4. 插件法 vs 裸 CDP 的战略判词

- 裸 CDP 依赖整浏览器实例成功暴露 `9222`，容易被 Win10 会话隔离、Profile 残留和 Chrome 参数吞噬问题击穿
- 插件法是在 **用户已打开、已登录、已在交互桌面中的真实 tab** 上做显式 attach
- 因此对于 `Profile 2` 真身账号接管，官方插件法是优先级更高的主路线

### 5. 远程 Gateway 架构建议

如果主脑/Gateway 不在 Win10 本机：

- Win10 应运行 **node host**
- Gateway 与 node host 保持 **tailnet-only**
- 不向公网暴露 relay/control 端口

---

## 七、Win10 全系统软件控制扩展（非浏览器）

### 1. 目标

Win10 节点不应只做浏览器代理，还应逐步扩展为：

- 记事本文本录入器
- IDE / OpenCode / Codex 启动与输入执行端
- 本地代码运行与结果回传节点

### 2. 当前可用官方主干

当前 OpenClaw 官方原生强项是：

- Gateway
- node host
- browser relay
- nodes / exec / browser 统一调度

也就是说，最稳的主干架构应是：

1. 主脑产出代码/指令
2. Win10 节点负责本地执行与软件侧动作
3. 浏览器或终端结果回传主脑

### 3. 技能库现状

ClawHub 检索已命中：

- `windows-ui-automation`
- `desktop-control-win`

但两者在非交互安装时均被 ClawHub 标记为：

```text
Warning: flagged as suspicious by VirusTotal Code Insight
Error: Use --force to install suspicious skills in non-interactive mode
```

### 4. 当前安全判词

在未完成技能包源码审计前，**禁止为了赶进度直接 `--force` 强装**。

正确顺序：

1. 先完成官方浏览器接管链
2. 若确需桌面控件技能，再对 `windows-ui-automation` / `desktop-control-win` 做只读审包
3. 确认无恶意行为、外传风险、危险执行链后，再决定是否安装

### 5. 对 OpenCode / Codex / IDE 的架构建议

最优长期链路应为：

- 主脑：生成代码、生成补丁、生成操作计划
- Win10：
  - 使用官方/审计通过的桌面控制技能打开 OpenCode / Codex / IDE
  - 粘贴主脑给出的代码/命令
  - 本地运行
- 浏览器 relay / 终端 / 文件结果：作为回执通道

这条链路成立后，Win10 才真正从“浏览器小弟”升级为“桌面操控官”。

---

## 八、实战判词与后续策略

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

### 本次 `Profile 2` 暴力夺回补充结论

本次已实做以下动作：

- `taskkill /F /IM chrome.exe /T`
- `taskkill /F /IM GoogleUpdate.exe /T`
- 删除 `User Data` 与 `Profile 2` 下常见 `Singleton*` 锁文件（若存在）
- 通过计划任务 `OpenClaw_CDP_Final` 以 `/it /rl HIGHEST /ru Administrator` 启动：
  - `chrome.exe --profile-directory="Profile 2" --remote-debugging-port=9222`

真实结果：

- `schtasks /run` 成功
- `schtasks /query /fo LIST /v` 显示任务处于“正在运行 / 交互方式/后台方式”
- 但 `curl http://127.0.0.1:9222/json/version` 仍返回 `Connection refused`
- 15 秒延时复核后仍未恢复

因此可追加定性：

> 若“临时目录 + 9222”可通，而“Profile 2 + 9222”在极限清场、删锁、计划任务 `/it` 后仍拒连，则可判定为 `Profile 2` 现有用户态会话/复用链持续吞掉 remote-debugging 参数，不是简单慢启动。

这种情况下，最稳策略不是继续盲点 `Profile 2`，而是：

1. 先用临时目录法保住 CDP 能力
2. 等主公允许后重启 Win10
3. 重启后第一时间在交互桌面里点 `Profile 2 --remote-debugging-port=9222`
4. 若仍失败，再考虑 `Profile 2` 数据层面的深度清障

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
