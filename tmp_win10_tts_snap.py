import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

print('=== Snapshot ttsmp3.com 页面 ===')
cmd = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --json'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
snap_out = stdout.read().decode('utf-8', 'ignore')
snap_err = stderr.read().decode('utf-8', 'ignore')

# 解析 JSON
try:
    snap_data = json.loads(snap_out)
    print(json.dumps(snap_data, indent=2, ensure_ascii=False)[:3000])
except:
    print('原始输出:')
    print(snap_out[:2000])
    if snap_err:
        print('STDERR:', snap_err[:500])

cli.close()
