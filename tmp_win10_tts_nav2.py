import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

print('=== 用 browser open 跳转到 ttsmp3.com ===')
cmd = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome open "https://ttsmp3.com/"'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
nav_out = stdout.read().decode('utf-8', 'ignore')
nav_err = stderr.read().decode('utf-8', 'ignore')
print(nav_out)
if nav_err:
    print('STDERR:', nav_err)

time.sleep(5)

print('')
print('=== 验证：tabs 列表 ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome tabs --json'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=30)
tabs_out = stdout2.read().decode('utf-8', 'ignore')
print(tabs_out)

cli.close()
