import paramiko, json

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 读取 Win10 配置文件全文
stdin, stdout, stderr = cli.exec_command('type C:\\Users\\Administrator\\.openclaw\\openclaw.json', timeout=30)
cfg_text = stdout.read().decode('utf-8', 'ignore')

print('=== Win10 openclaw.json 全文 ===')
print(cfg_text[:3000])

cli.close()
