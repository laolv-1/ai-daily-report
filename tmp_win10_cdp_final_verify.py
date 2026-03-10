import paramiko, textwrap
host='100.89.160.67'; user='Administrator'; pwd='As1231'
remote_script = r'''
import json, urllib.request, time
from pathlib import Path
from playwright.sync_api import sync_playwright

result = {
  'probe_9222_ok': False,
  'json_version': None,
  'connect_ok': False,
  'contexts': None,
  'pages_before': None,
  'youtube_title': None,
  'youtube_url': None,
  'avatar_btn_count': None,
  'sign_in_count': None,
  'login_state': None,
  'screenshot_path': None,
  'error': None,
}

try:
    with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=3) as r:
        result['json_version'] = json.loads(r.read().decode('utf-8', 'ignore'))
        result['probe_9222_ok'] = True
except Exception as e:
    result['error'] = 'probe_9222_failed:' + repr(e)

if result['probe_9222_ok']:
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
            result['connect_ok'] = True
            result['contexts'] = len(browser.contexts)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            result['pages_before'] = len(ctx.pages)
            page = ctx.new_page()
            page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(8000)
            result['youtube_title'] = page.title()
            result['youtube_url'] = page.url
            try:
                result['avatar_btn_count'] = page.locator('#avatar-btn').count()
            except Exception:
                result['avatar_btn_count'] = -1
            try:
                result['sign_in_count'] = page.locator('text=Sign in').count() + page.locator('text=登录').count()
            except Exception:
                result['sign_in_count'] = -1
            if (result['avatar_btn_count'] or 0) > 0 and (result['sign_in_count'] or 0) == 0:
                result['login_state'] = 'avatar_visible'
            elif (result['sign_in_count'] or 0) > 0:
                result['login_state'] = 'sign_in_visible'
            else:
                result['login_state'] = 'uncertain'
            shot = Path(r'C:\Users\Administrator\youtube_profile2_verify.png')
            page.screenshot(path=str(shot), full_page=True)
            result['screenshot_path'] = str(shot)
            browser.close()
    except Exception as e:
        result['error'] = 'cdp_connect_or_youtube_check_failed:' + repr(e)

report = Path(r'C:\Users\Administrator\cdp_verify_report.json')
report.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding='utf-8')
print(str(report))
'''
cli=paramiko.SSHClient(); cli.set_missing_host_key_policy(paramiko.AutoAddPolicy()); cli.connect(host, username=user, password=pwd, timeout=20)
sftp=cli.open_sftp()
remote=r'C:\Users\Administrator\cdp_verify_reporter.py'
with sftp.open(remote,'w') as f:
    f.write(textwrap.dedent(remote_script).strip()+"\r\n")
stdin, stdout, stderr = cli.exec_command(r'cmd /c python C:\Users\Administrator\cdp_verify_reporter.py', timeout=300)
out=stdout.read().decode('utf-8','ignore').strip()
err=stderr.read().decode('utf-8','ignore')
print(out)
if err.strip():
    print('=== STDERR ===\n'+err)
if out:
    stdin2, stdout2, stderr2 = cli.exec_command(r'type C:\Users\Administrator\cdp_verify_report.json', timeout=300)
    print(stdout2.read().decode('utf-8','ignore'))
    err2 = stderr2.read().decode('utf-8','ignore')
    if err2.strip():
        print('=== STDERR2 ===\n'+err2)
cli.close()
