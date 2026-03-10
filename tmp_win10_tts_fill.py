import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

test_text = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！"

print('=== 第三步：注入文本到 #voicetext ===')
# 使用 browser act 的 fill 动作
cmd = f'''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome act --kind fill --selector "#voicetext" --text "{test_text}"'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
fill_out = stdout.read().decode('utf-8', 'ignore')
fill_err = stderr.read().decode('utf-8', 'ignore')
print(fill_out)
if fill_err:
    print('STDERR:', fill_err)

time.sleep(2)

print('')
print('=== 第四步：选择中文语音 Zhiyu ===')
# 先 snapshot 看看下拉框的选项
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --selector "#sprachwahl"'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
snap_out = stdout2.read().decode('utf-8', 'ignore')
print(snap_out[:1500])

cli.close()
