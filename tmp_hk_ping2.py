import paramiko, json, textwrap

host='100.82.179.92'
user='root'
pwd='8ce42842#'

remote_script = textwrap.dedent(r'''
import json, urllib.request
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {
        "message": {"text": "只回复 PONG，不要寒暄。"},
        "agentId": "main"
    }
}
req = urllib.request.Request(
    "http://127.0.0.1:18800/a2a/jsonrpc",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read().decode("utf-8", "ignore"))
        print(json.dumps(resp, ensure_ascii=True, indent=2))
except Exception as e:
    print(json.dumps({"error": repr(e)}, ensure_ascii=True, indent=2))
''').strip()

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

sftp = cli.open_sftp()
remote_path = '/tmp/hk_ping_test.py'
with sftp.open(remote_path, 'w') as f:
    f.write(remote_script + '\n')

stdin, stdout, stderr = cli.exec_command(f'python3 {remote_path}', timeout=60)
out = stdout.read().decode('utf-8', 'ignore')
err = stderr.read().decode('utf-8', 'ignore')
print(out)
if err.strip():
    print('=== STDERR ===\n' + err)

cli.close()
