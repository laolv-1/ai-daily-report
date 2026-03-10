import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 先 snapshot 看看当前状态
print('=== 先 snapshot 确认文本框 ref ===')
cmd0 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --json'''
stdin0, stdout0, stderr0 = cli.exec_command(cmd0, timeout=60)
snap0 = stdout0.read().decode('utf-8', 'ignore')
print(snap0[:2000])

time.sleep(1)

# 用 fill 命令填充文本
print('')
print('=== 用 fill 命令填充文本 ===')
# fill 命令期望 JSON field descriptors
test_text = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！"
fill_data = json.dumps({"e15": test_text}, ensure_ascii=False)
cmd = f'''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome fill {fill_data}'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
fill_out = stdout.read().decode('utf-8', 'ignore')
fill_err = stderr.read().decode('utf-8', 'ignore')
print(fill_out)
if fill_err:
    print('STDERR:', fill_err[:500])

time.sleep(2)

# 验证
print('')
print('=== 验证文本已注入 ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --json'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
snap2 = stdout2.read().decode('utf-8', 'ignore')
print(snap2[:2000])

cli.close()
