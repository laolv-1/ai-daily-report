import paramiko, json

host='100.89.160.67'
user='Administrator'
pwd='As1231'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pwd, timeout=20)

# 读取 Win10 配置文件
stdin, stdout, stderr = cli.exec_command('type C:\\Users\\Administrator\\.openclaw\\openclaw.json', timeout=30)
cfg_text = stdout.read().decode('utf-8', 'ignore')

try:
    cfg = json.loads(cfg_text)
    
    # 检查模型配置
    lck_models = []
    primary_model = 'N/A'
    
    if 'models' in cfg and 'providers' in cfg['models'] and 'lck' in cfg['models']['providers']:
        lck_models = [m.get('id', 'N/A') for m in cfg['models']['providers']['lck'].get('models', [])]
    
    if 'agents' in cfg and 'defaults' in cfg['agents'] and 'model' in cfg['agents']['defaults']:
        primary_model = cfg['agents']['defaults']['model'].get('primary', 'N/A')
    
    print('=== Win10 模型配置 ===')
    print(f'lck providers models: {lck_models}')
    print(f'primary model: {primary_model}')
    
    # 检查 gateway 状态
    stdin2, stdout2, stderr2 = cli.exec_command('netstat -ano | findstr "LISTENING" | findstr "18789 18800"', timeout=15)
    listening = stdout2.read().decode('utf-8', 'ignore')
    
    print('')
    print('=== 监听端口 ===')
    print(listening.strip() if listening.strip() else '无相关端口监听')
    
except json.JSONDecodeError as e:
    print(f'配置文件解析失败：{e}')
    print('前 500 字符预览:')
    print(cfg_text[:500])

cli.close()
