import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

print('=== openclaw browser --help ===')
cmd = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --help'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=30)
out = stdout.read().decode('utf-8', 'ignore')
err = stderr.read().decode('utf-8', 'ignore')
print(out[:2500])
if err:
    print('STDERR:', err[:500])

print('')
print('=== openclaw browser act --help ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser act --help'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=30)
out2 = stdout2.read().decode('utf-8', 'ignore')
err2 = stderr2.read().decode('utf-8', 'ignore')
print(out2[:2500])
if err2:
    print('STDERR:', err2[:500])

cli.close()
