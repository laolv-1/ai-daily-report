import paramiko, json, time, textwrap

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

sftp = cli.open_sftp()

# 写入 JS 文件到 Win10
js_code = '''
() => {
    const textbox = document.querySelector("#voicetext");
    if (textbox) {
        textbox.value = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！";
        textbox.dispatchEvent(new Event("input", { bubbles: true }));
        return "TEXT_FILLED_OK";
    }
    return "TEXTBOX_NOT_FOUND";
}
'''

remote_js_path = 'C:\\Users\\Administrator\\tts_fill.js'
with sftp.open(remote_js_path, 'w') as f:
    f.write(js_code)

print('=== JS 文件已写入 Win10 ===')
print(f'路径：{remote_js_path}')

# 用 evaluate 执行 JS 文件
cmd = f'''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome act --kind evaluate --fn "file:{remote_js_path}"'''
print('')
print('=== 执行 evaluate ===')
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
eval_out = stdout.read().decode('utf-8', 'ignore')
eval_err = stderr.read().decode('utf-8', 'ignore')
print(eval_out)
if eval_err:
    print('STDERR:', eval_err[:500])

time.sleep(2)

# 验证
print('')
print('=== 验证：snapshot #voicetext ===')
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome snapshot --selector "#voicetext"'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
snap_out = stdout2.read().decode('utf-8', 'ignore')
print(snap_out[:1500])

sftp.close()
cli.close()
