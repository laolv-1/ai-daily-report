import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

test_text = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！"

# 用 evaluate 执行 JS 来注入文本
js_fill = f'''() => {{ document.querySelector("#voicetext").value = "{test_text}"; document.querySelector("#voicetext").dispatchEvent(new Event("input", {{ bubbles: true }})); return "OK"; }}'''

print('=== 用 evaluate 注入文本 ===')
cmd = f'''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome act --kind evaluate --fn "{js_fill}"'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
eval_out = stdout.read().decode('utf-8', 'ignore')
eval_err = stderr.read().decode('utf-8', 'ignore')
print(eval_out)
if eval_err:
    print('STDERR:', eval_err[:500])

time.sleep(2)

print('')
print('=== 验证文本已注入：snapshot ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --selector "#voicetext"'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
snap_out = stdout2.read().decode('utf-8', 'ignore')
print(snap_out[:1500])

cli.close()
