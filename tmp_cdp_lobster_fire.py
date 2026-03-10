import paramiko
import textwrap

host='100.89.160.67'
user='Administrator'
pwd='As1231'

remote_script = r'''
from pathlib import Path
import subprocess, time, os, urllib.request, json
from playwright.sync_api import sync_playwright

sop_path = Path(r"D:\来财\openclaw\SOP_防封接管与资产归档规范.md")
sop_text = """# SOP：防封接管与资产归档规范

## 一、禁止无头幽灵模式做正式账号动作
涉及登录、发视频、回帖、评论时，禁止使用 headless 浏览器、Session 0 幽灵窗口、临时 profile。它们只可用于探站、DOM 侦察、试车，不可作为正式发布主链。

## 二、必须接管 Chrome_龙虾出海（Profile 2）
正式账号动作统一且只能使用 Win10 桌面可见的 Chrome_龙虾出海（Profile 2）。优先通过 playwright.chromium.connect_over_cdp(\"http://127.0.0.1:9222\") 接管主公真实浏览器，继承 Cookies、LocalStorage、扩展、历史缓存与长期指纹连续性。

## 三、多媒体资产归档铁律
- 音频：D:\\来财\\音频
- 文档 / SOP / 技能：D:\\来财\\openclaw
禁止把多媒体资产乱放到 Downloads、Temp 或其他凭感觉创建的目录。
"""
sop_path.write_text(sop_text, encoding='utf-8')

launch_bat = Path(r"C:\Users\Administrator\launch_chrome_lobster_9222.bat")
launch_bat.write_text("""@echo off
setlocal
chcp 65001 >nul
set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if not exist \"%CHROME%\" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
taskkill /F /IM chrome.exe /T >nul 2>&1
ping 127.0.0.1 -n 3 >nul
start \"\" \"%CHROME%\" --profile-directory=\"Profile 2\" --remote-debugging-port=9222 --no-first-run --no-default-browser-check https://www.youtube.com
""", encoding='utf-8')

subprocess.run('schtasks /delete /tn OpenClaw_CDP_Lobster /f', shell=True, capture_output=True, text=True)
create = subprocess.run(r'schtasks /create /tn OpenClaw_CDP_Lobster /sc once /st 23:59 /tr "C:\Users\Administrator\launch_chrome_lobster_9222.bat" /ru Administrator /rp As1231 /rl HIGHEST /it /f', shell=True, capture_output=True, text=True)
run = subprocess.run(r'schtasks /run /tn OpenClaw_CDP_Lobster', shell=True, capture_output=True, text=True)

ready = False
version = None
for _ in range(20):
    time.sleep(1)
    try:
        with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2) as r:
            version = json.loads(r.read().decode('utf-8','ignore'))
            ready = True
            break
    except Exception:
        pass

result = {
    'sop_written': sop_path.exists(),
    'sop_path': str(sop_path),
    'task_create_rc': create.returncode,
    'task_run_rc': run.returncode,
    'cdp_ready': ready,
    'version_browser': (version or {}).get('Browser'),
    'youtube_login_state': None,
    'youtube_title': None,
    'youtube_url': None,
    'manual_hint': None,
}

if ready:
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            result['youtube_title'] = page.title()
            result['youtube_url'] = page.url
            sign_in = page.locator('text=Sign in').count() > 0 or page.locator('text=登录').count() > 0
            avatar = page.locator('button#avatar-btn').count() > 0
            if avatar and not sign_in:
                result['youtube_login_state'] = 'avatar_visible'
            elif sign_in:
                result['youtube_login_state'] = 'sign_in_visible'
            else:
                result['youtube_login_state'] = 'uncertain'
            browser.close()
    except Exception as e:
        result['youtube_login_state'] = 'cdp_connected_but_check_failed:' + repr(e)
else:
    result['manual_hint'] = '右键桌面快捷方式 Chrome_龙虾出海 → 属性 → 在目标末尾追加 --remote-debugging-port=9222，保存后双击打开。'

print(json.dumps(result, ensure_ascii=False, indent=2))
'''

cli=paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)
sftp=cli.open_sftp()
remote=r'C:\Users\Administrator\cdp_lobster_fire_and_verify.py'
with sftp.open(remote,'w') as f:
    f.write(textwrap.dedent(remote_script).strip()+"\r\n")
stdin, stdout, stderr = cli.exec_command(r'cmd /c python C:\Users\Administrator\cdp_lobster_fire_and_verify.py', timeout=300)
out=stdout.read().decode('utf-8','ignore')
err=stderr.read().decode('utf-8','ignore')
print(out)
if err.strip():
    print('=== STDERR ===\n'+err)
cli.close()
