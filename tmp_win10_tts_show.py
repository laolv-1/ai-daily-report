import paramiko, json, time, textwrap

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 第一步：检查当前已 attach 的 tabs
print('=== 第一步：检查已 attach 的标签页 ===')
stdin, stdout, stderr = cli.exec_command('"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome tabs --json', timeout=30)
tabs_out = stdout.read().decode('utf-8', 'ignore')
print(tabs_out[:1500])

cli.close()
