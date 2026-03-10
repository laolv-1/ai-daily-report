#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import socket
import urllib.parse
import urllib.request

TOKEN = "8545151429:AAGTiHUsUsH_VkYEtswD3I2v_7pDV9DO8S0"
CHAT_ID = "7392107275"

STATE_FILE = "/root/.openclaw/workspace/memory/zero_token_monitor_state.json"

TARGETS = {
    "laifu_aliyun": "100.82.179.92",
    "hk_dualhead": "100.119.68.81",
}

# 明确排除 Win10 节点
EXCLUDED = {"100.89.160.67"}

TIMEOUT_SECONDS = 2
PORT = 22


def load_state():
    if not os.path.exists(STATE_FILE):
        return {k: 0 for k in TARGETS}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in TARGETS:
            data.setdefault(k, 0)
        return data
    except Exception:
        return {k: 0 for k in TARGETS}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def check_host(ip):
    if ip in EXCLUDED:
        return True
    try:
        with socket.create_connection((ip, PORT), timeout=TIMEOUT_SECONDS):
            return True
    except Exception:
        return False


def send_alert(host_key, ip):
    text = f"🚨 掉线警报\n节点：{host_key}\nIP：{ip}\n连续2次探测失败"  # 纯文本卡片
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_notification": True,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=5):
        pass


def main():
    state = load_state()
    for key, ip in TARGETS.items():
        ok = check_host(ip)
        if ok:
            state[key] = 0
        else:
            state[key] = state.get(key, 0) + 1
            if state[key] == 2:
                send_alert(key, ip)
    save_state(state)


if __name__ == "__main__":
    main()
