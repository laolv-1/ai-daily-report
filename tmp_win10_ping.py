import paramiko, json, textwrap

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 检查 Win10 配置中的模型版本
stdin, stdout, stderr = cli.exec_command('findstr /C:"gpt-5." C:\\Users\\Administrator\\.openclaw\\openclaw.json', timeout=30)
model_check = stdout.read().decode('utf-8', 'ignore')

# 检查 Gateway 状态
stdin2, stdout2, stderr2 = cli.exec_command('netstat -ano | findstr ":18789"', timeout=15)
port_check = stdout2.read().decode('utf-8', 'ignore')

# 检查 A2A 端口
stdin3, stdout3, stderr3 = cli.exec_command('netstat -ano | findstr ":18800"', timeout=15)
a2a_check = stdout3.read().decode('utf-8', 'ignore')

print('=== 模型配置检查 ===')
print(model_check.strip())
print('')
print('=== Gateway 端口 (18789) ===')
print(port_check.strip())
print('')
print('=== A2A 端口 (18800) ===')
print(a2a_check.strip())

cli.close()
