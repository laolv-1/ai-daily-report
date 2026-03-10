import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

print('=== 第二步：跳转到 ttsmp3.com ===')
cmd = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome act --ref A3351FCFF985591AD06C0C1930F34D83 --kind navigate --text "https://ttsmp3.com/"'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
nav_out = stdout.read().decode('utf-8', 'ignore')
nav_err = stderr.read().decode('utf-8', 'ignore')
print(nav_out)
if nav_err:
    print('STDERR:', nav_err)

time.sleep(3)

print('')
print('=== 验证跳转：snapshot ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --ref A3351FCFF985591AD06C0C1930F34D83'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
snap_out = stdout2.read().decode('utf-8', 'ignore')
print(snap_out[:2000])

cli.close()
