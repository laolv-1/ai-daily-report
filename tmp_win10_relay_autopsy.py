import paramiko, textwrap
host='100.89.160.67'; user='Administrator'; pwd='As1231'
remote_script = r'''
import json, subprocess, pathlib, re
from pathlib import Path

out = {}

def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    return {
        'rc': p.returncode,
        'stdout': p.stdout[-6000:],
        'stderr': p.stderr[-3000:],
    }

cfg = Path(r'C:\Users\Administrator\.openclaw\openclaw.json')
out['config_exists'] = cfg.exists()
out['gateway_token'] = None
out['gateway_port'] = None
out['gateway_bind'] = None
out['gateway_mode'] = None
if cfg.exists():
    try:
        data = json.loads(cfg.read_text(encoding='utf-8'))
        gw = data.get('gateway') or {}
        auth = gw.get('auth') or {}
        out['gateway_token'] = auth.get('token')
        out['gateway_port'] = gw.get('port')
        out['gateway_bind'] = gw.get('bind')
        out['gateway_mode'] = gw.get('mode')
    except Exception as e:
        out['config_parse_error'] = repr(e)

out['netstat_18789'] = run(r'cmd /c netstat -ano | findstr :18789')
out['netstat_18791'] = run(r'cmd /c netstat -ano | findstr :18791')
out['netstat_18792'] = run(r'cmd /c netstat -ano | findstr :18792')
out['tasklist_node'] = run(r'cmd /c tasklist /v | findstr /i node.exe')
out['tasklist_openclaw'] = run(r'cmd /c tasklist /v | findstr /i openclaw')
out['gateway_status'] = run(r'cmd /c "C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" gateway status')
out['browser_status'] = run(r'cmd /c "C:\Users\Administrator\AppData\Roaming\npm\openclaw.cmd" browser status')
out['schtasks_query'] = run(r'cmd /c schtasks /query /tn "OpenClaw Gateway" /v /fo list')

# 常见日志位
candidate_logs = [
    Path(r'C:\Users\Administrator\.openclaw\gateway.log'),
    Path(r'C:\Users\Administrator\.openclaw\logs'),
    Path(r'C:\Users\Administrator\gateway_diag.log'),
    Path(r'C:\Users\Administrator\register_task.log'),
]
logs = {}
for p in candidate_logs:
    if p.is_dir():
        items = []
        for child in sorted(p.glob('*'))[-8:]:
            try:
                items.append({
                    'name': child.name,
                    'size': child.stat().st_size,
                    'tail': child.read_text(encoding='utf-8', errors='ignore')[-2500:] if child.is_file() else None,
                })
            except Exception as e:
                items.append({'name': child.name, 'error': repr(e)})
        logs[str(p)] = items
    elif p.exists():
        try:
            logs[str(p)] = p.read_text(encoding='utf-8', errors='ignore')[-4000:]
        except Exception as e:
            logs[str(p)] = {'error': repr(e)}
out['logs'] = logs

# 再找一轮 .openclaw 下可能相关日志
extra = []
root = Path(r'C:\Users\Administrator\.openclaw')
if root.exists():
    for child in sorted(root.rglob('*')):
        s = str(child).lower()
        if any(k in s for k in ['log', 'gateway', 'browser']):
            try:
                if child.is_file():
                    extra.append({'path': str(child), 'size': child.stat().st_size})
            except Exception:
                pass
out['extra_related_files'] = extra[-30:]

print(json.dumps(out, ensure_ascii=False, indent=2))
'''
cli=paramiko.SSHClient(); cli.set_missing_host_key_policy(paramiko.AutoAddPolicy()); cli.connect(host, username=user, password=pwd, timeout=20)
sftp=cli.open_sftp()
remote=r'C:\Users\Administrator\relay_autopsy.py'
with sftp.open(remote,'w') as f:
    f.write(textwrap.dedent(remote_script).strip()+"\r\n")
stdin, stdout, stderr = cli.exec_command(r'cmd /c python C:\Users\Administrator\relay_autopsy.py', timeout=300)
out=stdout.read().decode('utf-8','ignore')
err=stderr.read().decode('utf-8','ignore')
print(out)
if err.strip():
    print('=== STDERR ===\n'+err)
cli.close()
