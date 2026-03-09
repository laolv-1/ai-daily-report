#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config.json'
BOT_SESSION = str(BASE_DIR / 'bot_control')
USER_SESSION = str(BASE_DIR / 'user_operator')
LOG_PATH = BASE_DIR / 'broadcast.log'

DEFAULT_CONFIG = {
    'api_id': 31204443,
    'api_hash': 'db19af107c06da4dc9a6d1c50c58a0f6',
    'bot_token': '8737672051:AAH9NkDpSW8YwKs18g8RAcKJn4Cysu9VoFM',
    'admin_ids': [7392107275],
    'announcement_msg': '这里填写你的合规公告内容',
    'interval_minutes': 30,
    'approved_groups': [],
    'discovered_groups': [],
    'is_running': False,
    'last_broadcast_at': None,
    'last_round_summary': '',
    'audit_log': []
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8'), logging.StreamHandler()]
)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    if 'whitelist_groups' in data and not merged.get('approved_groups'):
        merged['approved_groups'] = [{'id': int(x), 'title': str(x)} for x in data.get('whitelist_groups', [])]
    return merged


def save_config(data: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def append_audit(data: dict[str, Any], message: str) -> None:
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = f'[{stamp}] {message}'
    data.setdefault('audit_log', []).append(row)
    data['audit_log'] = data['audit_log'][-30:]
    save_config(data)
    logging.info(message)


def is_allowed_admin(data: dict[str, Any], user_id: int | None) -> bool:
    return user_id is not None and user_id in set(data.get('admin_ids', []))


def format_group_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '暂无'
    return '\n'.join([f"{idx}. {item.get('title', 'unknown')} | {item.get('id')}" for idx, item in enumerate(rows, start=1)])


def parse_selection(raw: str) -> list[int]:
    raw = raw.replace('\n', ' ').replace(',', ' ')
    out: list[int] = []
    for part in raw.split():
        try:
            out.append(int(part.strip()))
        except ValueError:
            continue
    return sorted(set(out))


async def safe_reply(event, text: str) -> None:
    await event.reply(text)


async def discover_groups(user_client: TelegramClient) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    async for dialog in user_client.iter_dialogs():
        entity = dialog.entity
        if getattr(dialog, 'is_group', False) or getattr(dialog, 'is_channel', False):
            if isinstance(entity, (Channel, Chat)):
                found.append({
                    'id': int(getattr(entity, 'id', 0)) if not str(getattr(entity, 'id', '')).startswith('-100') else int(getattr(entity, 'id')),
                    'peer_id': int(dialog.id),
                    'title': dialog.name or str(dialog.id),
                })
    unique = {}
    for item in found:
        unique[int(item['peer_id'])] = {'id': int(item['peer_id']), 'title': item['title']}
    return list(unique.values())


async def fetch_approved_targets(user_client: TelegramClient, approved_rows: list[dict[str, Any]]):
    entities = []
    for row in approved_rows:
        gid = int(row['id'])
        try:
            ent = await user_client.get_entity(gid)
            if isinstance(ent, (Channel, Chat)):
                entities.append(ent)
        except Exception as exc:
            logging.warning('群组 %s 获取失败: %s', gid, exc)
    return entities


async def broadcaster_loop(bot_client: TelegramClient, user_client: TelegramClient):
    while True:
        data = load_config()
        if not data.get('is_running'):
            await asyncio.sleep(5)
            continue

        msg = (data.get('announcement_msg') or '').strip()
        interval = max(int(data.get('interval_minutes', 30)), 1)
        approved = data.get('approved_groups', [])

        if not msg:
            append_audit(data, '广播未启动：announcement_msg 为空')
            data['is_running'] = False
            save_config(data)
            await asyncio.sleep(5)
            continue
        if not approved:
            append_audit(data, '广播未启动：授权池为空，请先 /discover 再 /approve_all 或 /approve')
            data['is_running'] = False
            save_config(data)
            await asyncio.sleep(5)
            continue

        targets = await fetch_approved_targets(user_client, approved)
        if not targets:
            append_audit(data, '广播未启动：授权池群组均不可达')
            data['is_running'] = False
            save_config(data)
            await asyncio.sleep(10)
            continue

        append_audit(data, f'开始合规广播，本轮目标 {len(targets)} 个，群间隔 {interval} 分钟')
        ok_count = 0
        fail_count = 0

        for idx, target in enumerate(targets, start=1):
            data = load_config()
            if not data.get('is_running'):
                append_audit(data, '广播被管理员手动停止')
                break
            try:
                await user_client.send_message(target, msg)
                ok_count += 1
                append_audit(data, f'已发送到授权群：{getattr(target, "title", getattr(target, "id", "unknown"))} ({idx}/{len(targets)})')
            except FloodWaitError as exc:
                fail_count += 1
                wait_seconds = int(exc.seconds) + 5
                append_audit(data, f'触发 FloodWait，暂停 {wait_seconds}s 后继续')
                await asyncio.sleep(wait_seconds)
            except Exception as exc:
                fail_count += 1
                append_audit(data, f'发送失败：{getattr(target, "id", "unknown")} / {exc}')

            if idx < len(targets):
                await asyncio.sleep(interval * 60)

        data = load_config()
        data['last_broadcast_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['last_round_summary'] = f'本轮完成：成功 {ok_count}，失败 {fail_count}，目标 {len(targets)}'
        save_config(data)
        append_audit(data, data['last_round_summary'])
        await bot_client.send_message(data['admin_ids'][0], f'📣 合规广播一轮结束\n{data["last_round_summary"]}')
        await asyncio.sleep(max(interval * 60, 300))


async def main():
    cfg = load_config()
    api_id = int(cfg['api_id'])
    api_hash = str(cfg['api_hash'])
    bot_token = str(cfg['bot_token'])

    bot_client = TelegramClient(BOT_SESSION, api_id, api_hash)
    user_client = TelegramClient(USER_SESSION, api_id, api_hash)

    await bot_client.start(bot_token=bot_token)
    await user_client.connect()
    if not await user_client.is_user_authorized():
        raise RuntimeError('操作员账号尚未授权，请先运行 login.py 生成 user_operator.session')

    @bot_client.on(events.NewMessage(pattern=r'^/msg(?:\s+([\s\S]+))?$'))
    async def cmd_msg(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        text = event.pattern_match.group(1)
        if not text:
            await safe_reply(event, '用法：/msg 这里填写公告内容')
            return
        data['announcement_msg'] = text.strip()
        append_audit(data, f'管理员 {event.sender_id} 更新了公告内容')
        await safe_reply(event, '✅ 公告内容已更新')

    @bot_client.on(events.NewMessage(pattern=r'^/discover$'))
    async def cmd_discover(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        rows = await discover_groups(user_client)
        data['discovered_groups'] = rows
        append_audit(data, f'管理员 {event.sender_id} 扫描到 {len(rows)} 个候选群')
        preview = format_group_rows(rows[:50])
        tail = '\n……' if len(rows) > 50 else ''
        await safe_reply(event, f'🔎 已发现 {len(rows)} 个候选群\n\n{preview}{tail}\n\n可用：/approve_all 或 /approve 1 2 3')

    @bot_client.on(events.NewMessage(pattern=r'^/approve_all$'))
    async def cmd_approve_all(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        rows = data.get('discovered_groups', [])
        if not rows:
            await safe_reply(event, '❌ 候选池为空，先执行 /discover')
            return
        data['approved_groups'] = rows
        append_audit(data, f'管理员 {event.sender_id} 一键批准了全部候选群，共 {len(rows)} 个')
        await safe_reply(event, f'✅ 已一键批准 {len(rows)} 个群进入授权池')

    @bot_client.on(events.NewMessage(pattern=r'^/approve(?:\s+([\s\S]+))?$'))
    async def cmd_approve(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        raw = event.pattern_match.group(1) or ''
        picks = parse_selection(raw)
        rows = data.get('discovered_groups', [])
        if not rows:
            await safe_reply(event, '❌ 候选池为空，先执行 /discover')
            return
        if not picks:
            await safe_reply(event, '用法：/approve 1 2 3')
            return
        chosen = []
        for idx in picks:
            if 1 <= idx <= len(rows):
                chosen.append(rows[idx - 1])
        if not chosen:
            await safe_reply(event, '❌ 没有命中有效序号')
            return
        existing = {int(x['id']): x for x in data.get('approved_groups', [])}
        for item in chosen:
            existing[int(item['id'])] = item
        data['approved_groups'] = list(existing.values())
        append_audit(data, f'管理员 {event.sender_id} 批准了 {len(chosen)} 个群进入授权池')
        await safe_reply(event, '✅ 已批准以下群进入授权池\n' + format_group_rows(chosen))

    @bot_client.on(events.NewMessage(pattern=r'^/remove(?:\s+([\s\S]+))?$'))
    async def cmd_remove(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        raw = event.pattern_match.group(1) or ''
        picks = parse_selection(raw)
        rows = data.get('approved_groups', [])
        if not rows:
            await safe_reply(event, '❌ 当前授权池为空')
            return
        if not picks:
            await safe_reply(event, '用法：/remove 1 2 3  （序号基于当前授权池）')
            return
        kept, removed = [], []
        for idx, item in enumerate(rows, start=1):
            if idx in picks:
                removed.append(item)
            else:
                kept.append(item)
        data['approved_groups'] = kept
        append_audit(data, f'管理员 {event.sender_id} 从授权池移除了 {len(removed)} 个群')
        await safe_reply(event, '🗑️ 已移出以下群\n' + (format_group_rows(removed) if removed else '暂无命中'))

    @bot_client.on(events.NewMessage(pattern=r'^/targets$'))
    async def cmd_targets(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        rows = data.get('approved_groups', [])
        await safe_reply(event, f'📚 当前授权池共 {len(rows)} 个\n\n{format_group_rows(rows[:80])}')

    @bot_client.on(events.NewMessage(pattern=r'^/time(?:\s+(\d+))?$'))
    async def cmd_time(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        val = event.pattern_match.group(1)
        if not val:
            await safe_reply(event, '用法：/time 30  （单位：分钟）')
            return
        minutes = max(int(val), 1)
        data['interval_minutes'] = minutes
        append_audit(data, f'管理员 {event.sender_id} 将群间隔改为 {minutes} 分钟')
        await safe_reply(event, f'✅ 合规发送间隔已设为 {minutes} 分钟/群')

    @bot_client.on(events.NewMessage(pattern=r'^/start$'))
    async def cmd_start(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        if not data.get('approved_groups'):
            await safe_reply(event, '❌ 授权池为空，先执行 /discover，再 /approve_all 或 /approve')
            return
        if not (data.get('announcement_msg') or '').strip():
            await safe_reply(event, '❌ 公告内容为空，先执行 /msg')
            return
        data['is_running'] = True
        append_audit(data, f'管理员 {event.sender_id} 启动了合规广播')
        await safe_reply(event, '🟢 已开始合规广播（仅已批准授权池，严格按分钟间隔发送）')

    @bot_client.on(events.NewMessage(pattern=r'^/stop$'))
    async def cmd_stop(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        data['is_running'] = False
        append_audit(data, f'管理员 {event.sender_id} 停止了合规广播')
        await safe_reply(event, '🛑 已停止广播')

    @bot_client.on(events.NewMessage(pattern=r'^/status$'))
    async def cmd_status(event):
        data = load_config()
        if not is_allowed_admin(data, event.sender_id):
            return
        audit = '\n'.join(data.get('audit_log', [])[-8:]) or '暂无日志'
        text = (
            '📊 合规广播状态\n'
            f'运行中：{data.get("is_running")}\n'
            f'群间隔：{data.get("interval_minutes")} 分钟\n'
            f'候选池数：{len(data.get("discovered_groups", []))}\n'
            f'授权池数：{len(data.get("approved_groups", []))}\n'
            f'最近一轮：{data.get("last_round_summary") or "暂无"}\n'
            f'最近发送：{data.get("last_broadcast_at") or "暂无"}\n\n'
            '🧾 最近审计\n'
            f'{audit}'
        )
        await safe_reply(event, text)

    append_audit(cfg, '控制端与操作员端已启动，等待管理员指令')
    asyncio.create_task(broadcaster_loop(bot_client, user_client))
    await bot_client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
