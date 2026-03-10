import paramiko, json, textwrap

host='100.82.179.92'
user='root'
pwd='8ce42842#'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 读取来福配置
stdin, stdout, stderr = cli.exec_command('cat /root/.openclaw/openclaw.json', timeout=30)
cfg_text = stdout.read().decode('utf-8', 'ignore')
cfg = json.loads(cfg_text)

# 修改 lck 模型
if 'models' in cfg and 'providers' in cfg['models'] and 'lck' in cfg['models']['providers']:
    lck_models = cfg['models']['providers']['lck'].get('models', [])
    for m in lck_models:
        if m.get('id') == 'gpt-5.4':
            m['id'] = 'gpt-5.2'
            m['name'] = 'GPT-5.2'
    
    # 修改默认模型
    if 'agents' in cfg and 'defaults' in cfg['agents'] and 'model' in cfg['agents']['defaults']:
        primary = cfg['agents']['defaults']['model'].get('primary', '')
        if 'gpt-5.4' in primary:
            cfg['agents']['defaults']['model']['primary'] = primary.replace('gpt-5.4', 'gpt-5.2')
    
    # 修改 alias 映射
    if 'agents' in cfg and 'defaults' in cfg['agents'] and 'models' in cfg['agents']['defaults']:
        models_map = cfg['agents']['defaults']['models']
        if 'lck/gpt-5.4' in models_map:
            models_map['lck/gpt-5.2'] = models_map.pop('lck/gpt-5.4')
            models_map['lck/gpt-5.2']['alias'] = 'lck'

# 写回
new_cfg = json.dumps(cfg, ensure_ascii=False, indent=2)
stdin2, stdout2, stderr2 = cli.exec_command(f"cat > /root/.openclaw/openclaw.json << 'JSONEOF'\n{new_cfg}\nJSONEOF", timeout=30)
err2 = stderr2.read().decode('utf-8', 'ignore')

# 验证
stdin3, stdout3, stderr3 = cli.exec_command('grep -o "gpt-5.[0-9]" /root/.openclaw/openclaw.json | sort | uniq', timeout=15)
verify = stdout3.read().decode('utf-8', 'ignore')

print(f'修改完成，当前来福配置中的模型版本：{verify.strip()}')
if err2.strip():
    print(f'写回错误：{err2}')

cli.close()
