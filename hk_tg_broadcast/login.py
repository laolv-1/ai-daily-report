#!/usr/bin/env python3
from pathlib import Path
from telethon import TelegramClient

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config.json'
USER_SESSION = str(BASE_DIR / 'user_operator')


def main():
    import json
    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    client = TelegramClient(USER_SESSION, int(cfg['api_id']), str(cfg['api_hash']))
    client.start()
    me = client.loop.run_until_complete(client.get_me())
    print('登录成功：', getattr(me, 'id', 'unknown'), getattr(me, 'username', ''))
    client.disconnect()


if __name__ == '__main__':
    main()
