import paramiko, json, time

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 写入 JS 文件
js_fill = '''
() => {
    const textbox = document.querySelector("#voicetext");
    if (textbox) {
        textbox.value = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！";
        textbox.dispatchEvent(new Event("input", { bubbles: true }));
        return "TEXT_FILLED_OK";
    }
    // 备用选择器
    const textbox2 = document.querySelector("[aria-label='your text here']");
    if (textbox2) {
        textbox2.value = "主公，我是来福！您亲眼看着我把这段文字变成声音了吗？这就为您下载！";
        textbox2.dispatchEvent(new Event("input", { bubbles: true }));
        return "TEXT_FILLED_OK_ALT";
    }
    return "TEXTBOX_NOT_FOUND";
}
'''

sftp = cli.open_sftp()
with sftp.open('C:\\Users\\Administrator\\tts_fill2.js', 'w') as f:
    f.write(js_fill)
sftp.close()

print('=== 注入文本 ===')
cmd = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome evaluate "file:C:\\Users\\Administrator\\tts_fill2.js"'''
stdin, stdout, stderr = cli.exec_command(cmd, timeout=60)
eval_out = stdout.read().decode('utf-8', 'ignore')
eval_err = stderr.read().decode('utf-8', 'ignore')
print(eval_out)
if eval_err:
    print('STDERR:', eval_err[:500])

time.sleep(2)

print('')
print('=== 选择中文语音 Chinese Mandarin / Zhiyu ===')
# 用 select 命令
cmd2 = '''"C:\\Users\\Administrator\\AppData\\Roaming\\npm\\openclaw.cmd" browser --browser-profile chrome select e16 "Chinese Mandarin / Zhiyu"'''
stdin2, stdout2, stderr2 = cli.exec_command(cmd2, timeout=60)
sel_out = stdout2.read().decode('utf-8', 'ignore')
sel_err = stderr2.read().decode('utf-8', 'ignore')
print(sel_out)
if sel_err:
    print('STDERR:', sel_err[:500])

cli.close()
