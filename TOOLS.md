# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.


## A2A Gateway (Agent-to-Agent Communication)

你有一个 A2A Gateway 插件运行在 18800 端口。

### Peers

| Peer | IP | Auth Token |
|------|-----|------------|
| laifu_minion | 100.82.179.92 | d310cbdb76ae3110415577cffee4382833d321a12e2e32e3 |

### 发送方式

```bash
node /root/.openclaw/workspace/plugins/a2a-gateway/skill/scripts/a2a-send.mjs \
  --peer-url http://100.82.179.92:18800 \
  --token d310cbdb76ae3110415577cffee4382833d321a12e2e32e3 \
  --message "YOUR MESSAGE HERE"
```
