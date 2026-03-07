#!/usr/bin/env python3
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PEER_URL = "http://100.82.179.92:18800"
AGENT_CARD_URL = f"{PEER_URL}/.well-known/agent-card.json"
A2A_SCRIPT = "/root/.openclaw/workspace/plugins/a2a-gateway/skill/scripts/a2a-send.mjs"
TOKEN = "d310cbdb76ae3110415577cffee4382833d321a12e2e32e3"
STATE_PATH = Path("/root/.openclaw/workspace/memory/a2a_heartbeat_state.json")
LOG_PATH = Path("/root/.openclaw/workspace/memory/a2a_heartbeat_monitor.log")
FAIL_THRESHOLD = 3
TIMEOUT_SECONDS = 20
TG_BOT_TOKEN = "8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0"
TG_CHAT_ID = "7392107275"


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)



def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"consecutive_failures": 0, "last_ok": None, "last_alert_at": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"consecutive_failures": 0, "last_ok": None, "last_alert_at": None}



def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")



def http_get(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "a2a-heartbeat-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")



def send_telegram_alert(text: str) -> None:
    data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()



def run_a2a_ping() -> str:
    cmd = [
        "node",
        A2A_SCRIPT,
        "--peer-url",
        PEER_URL,
        "--token",
        TOKEN,
        "--non-blocking",
        "--wait",
        "--timeout-ms",
        "45000",
        "--poll-ms",
        "1000",
        "--message",
        "@laifu 只回复 PONG，不要寒暄。",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=70)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"A2A ping failed rc={proc.returncode} stdout={out[:500]} stderr={err[:500]}")
    return out



def main() -> int:
    state = load_state()
    hostname = socket.gethostname()
    try:
        card = http_get(AGENT_CARD_URL, TIMEOUT_SECONDS)
        if '"name":"来福"' not in card and '"name": "来福"' not in card:
            raise RuntimeError("agent-card 返回异常，未识别到来福")
        ping_out = run_a2a_ping()
        if "PONG" not in ping_out.upper():
            raise RuntimeError(f"A2A 未回 PONG，实际输出: {ping_out[:500]}")
        state["consecutive_failures"] = 0
        state["last_ok"] = int(time.time())
        save_state(state)
        log(f"A2A 心跳成功 hostname={hostname}")
        return 0
    except Exception as e:
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
        state["last_error"] = str(e)
        save_state(state)
        log(f"A2A 心跳失败 第{state['consecutive_failures']}次 hostname={hostname} error={e}")
        if state["consecutive_failures"] >= FAIL_THRESHOLD:
            last_alert_at = int(state.get("last_alert_at") or 0)
            now = int(time.time())
            if now - last_alert_at >= 1800:
                alert = (
                    "【A2A离线告警】\n"
                    f"节点: 来福\n"
                    f"地址: {PEER_URL}\n"
                    f"连续失败: {state['consecutive_failures']} 次\n"
                    f"错误: {e}\n"
                    "判定: A2A 神经链路可能离线，请立即排查。"
                )
                try:
                    send_telegram_alert(alert)
                    state["last_alert_at"] = now
                    save_state(state)
                    log("已发送 Telegram 离线告警")
                except Exception as alert_err:
                    log(f"Telegram 告警发送失败 error={alert_err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
