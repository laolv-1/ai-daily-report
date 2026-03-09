import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

BASE = Path('/root/.openclaw/workspace')
STATE = Path('/root/.openclaw')
OPENCLAW_JSON = STATE / 'openclaw.json'
ROUTER_JSON = BASE / 'llm_router.json'
HB_STATE = BASE / 'memory' / 'a2a_heartbeat_state.json'
HB_LOG = BASE / 'memory' / 'a2a_heartbeat_monitor.log'

app = FastAPI(title='Laicai Control Deck', version='0.1.0')
_cache: dict[str, tuple[float, Any]] = {}


def _read_json(path: Path, default: Any):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def _write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def _cache_get(key: str, ttl: int, loader):
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    val = loader()
    _cache[key] = (now, val)
    return val


def _derive_fleet_status():
    hb = _read_json(HB_STATE, {})
    last_ok = hb.get('last_ok', 0)
    age = int(time.time() - last_ok) if last_ok else None
    laifu_ok = bool(last_ok and age is not None and age < 900)
    return {
        'main': {'name': '来财', 'status': 'online', 'color': 'green', 'detail': '主脑在线'},
        'laifu': {'name': '来福', 'status': 'online' if laifu_ok else 'warn', 'color': 'green' if laifu_ok else 'yellow', 'detail': f'最近心跳 {age}s 前' if age is not None else '暂无心跳'},
        'hk': {'name': 'HK', 'status': 'online', 'color': 'green', 'detail': 'A2A 已合龙 / PONG 通过'},
        'lobster': {'name': '龙虾小弟', 'status': 'standby', 'color': 'gray', 'detail': '待激活槽位'},
    }


def _apply_router_to_openclaw(default_model: str, route: dict):
    cfg = _read_json(OPENCLAW_JSON, {})
    cfg.setdefault('models', {}).setdefault('providers', {})
    provider_block = cfg['models']['providers'].setdefault(route['provider'], {})
    provider_block['baseUrl'] = route['baseUrl']
    provider_block['apiKey'] = route['apiKey']
    provider_block.setdefault('api', 'openai-completions')
    provider_block.setdefault('models', [])
    found = False
    for item in provider_block['models']:
        if item.get('id') == route['model']:
            found = True
            break
    if not found:
        provider_block['models'].append({
            'id': route['model'],
            'name': route['model'],
            'reasoning': False,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 128000,
            'maxTokens': 8192,
        })
    cfg.setdefault('agents', {}).setdefault('defaults', {}).setdefault('model', {})['primary'] = default_model
    cfg['agents']['defaults'].setdefault('models', {})[default_model] = {'alias': route.get('alias', route['provider'])}
    _write_json(OPENCLAW_JSON, cfg)


class SwitchModelReq(BaseModel):
    modelKey: str


class AddRouteReq(BaseModel):
    provider: str
    model: str
    alias: str | None = None
    baseUrl: str
    apiKey: str
    enabled: bool = True
    notes: str | None = ''


@app.get('/api/state')
def api_state():
    router = _cache_get('router', 3, lambda: _read_json(ROUTER_JSON, {}))
    cfg = _cache_get('cfg', 3, lambda: _read_json(OPENCLAW_JSON, {}))
    return JSONResponse({
        'router': router,
        'openclawDefaultModel': cfg.get('agents', {}).get('defaults', {}).get('model', {}).get('primary'),
        'fleet': _derive_fleet_status(),
    })


@app.post('/api/model/switch')
def api_switch(req: SwitchModelReq):
    router = _read_json(ROUTER_JSON, {})
    routes = router.get('routes', [])
    route = next((r for r in routes if f"{r.get('provider')}/{r.get('model')}" == req.modelKey), None)
    if not route:
        raise HTTPException(status_code=404, detail='route not found')
    router['defaultModel'] = req.modelKey
    router['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    _write_json(ROUTER_JSON, router)
    _apply_router_to_openclaw(req.modelKey, route)
    _cache.clear()
    return {'ok': True, 'defaultModel': req.modelKey}


@app.post('/api/model/add')
def api_add(req: AddRouteReq):
    router = _read_json(ROUTER_JSON, {'version': 1, 'updatedAt': '', 'defaultModel': '', 'routes': []})
    route = {
        'id': f"{req.provider}-{req.model}".replace('/', '-'),
        'provider': req.provider,
        'model': req.model,
        'alias': req.alias or req.provider,
        'baseUrl': req.baseUrl,
        'apiKey': req.apiKey,
        'enabled': req.enabled,
        'notes': req.notes or ''
    }
    router.setdefault('routes', []).append(route)
    router['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if not router.get('defaultModel'):
        router['defaultModel'] = f"{req.provider}/{req.model}"
    _write_json(ROUTER_JSON, router)
    _cache.clear()
    return {'ok': True, 'route': route}


@app.get('/', response_class=HTMLResponse)
def home():
    html = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>来财 · 全域指挥舱</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
<div class="max-w-7xl mx-auto p-6 space-y-6">
  <div class="flex items-center justify-between">
    <div><h1 class="text-3xl font-bold">🦞 来财 · 全域指挥舱</h1><p class="text-slate-400 mt-2">极轻量 / 单进程 / 短缓存 / 无重算</p></div>
    <div id="defaultBadge" class="px-4 py-2 rounded-full bg-emerald-600 font-semibold">加载中</div>
  </div>
  <div class="grid md:grid-cols-2 gap-6">
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <h2 class="text-xl font-semibold mb-4">⚙️ 模型路由区</h2>
      <div id="routes" class="space-y-3"></div>
      <div class="mt-5 grid grid-cols-1 gap-3">
        <input id="provider" class="bg-slate-800 rounded-xl p-3" placeholder="provider，如 cheap" />
        <input id="model" class="bg-slate-800 rounded-xl p-3" placeholder="model，如 gpt-lite" />
        <input id="alias" class="bg-slate-800 rounded-xl p-3" placeholder="alias，如 cheap" />
        <input id="baseUrl" class="bg-slate-800 rounded-xl p-3" placeholder="baseUrl" />
        <input id="apiKey" class="bg-slate-800 rounded-xl p-3" placeholder="apiKey" />
        <input id="notes" class="bg-slate-800 rounded-xl p-3" placeholder="notes" />
        <button onclick="addRoute()" class="bg-cyan-600 hover:bg-cyan-500 rounded-xl px-4 py-3 font-semibold">新增模型通道</button>
      </div>
    </section>
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <h2 class="text-xl font-semibold mb-4">🛰️ A2A 舰队监控区</h2>
      <div id="fleet" class="grid sm:grid-cols-2 gap-4"></div>
      <div class="mt-5 text-sm text-slate-400">说明：来福状态取自本地心跳落盘；HK 状态基于已合龙链路；龙虾小弟为预留灰位。</div>
    </section>
  </div>
</div>
<script>
async function loadState(){
  const res = await fetch('/api/state');
  const data = await res.json();
  document.getElementById('defaultBadge').innerText = '当前默认：' + data.router.defaultModel;
  const routes = document.getElementById('routes');
  routes.innerHTML='';
  for(const r of data.router.routes){
    const key = `${r.provider}/${r.model}`;
    const active = key===data.router.defaultModel;
    const card = document.createElement('div');
    card.className='rounded-2xl border ' + (active ? 'border-emerald-500 bg-emerald-950/30' : 'border-slate-800 bg-slate-950') + ' p-4';
    card.innerHTML = `<div class="flex items-start justify-between gap-3"><div><div class="font-semibold text-lg">${key}</div><div class="text-slate-400 text-sm mt-1">${r.baseUrl}</div><div class="text-slate-500 text-xs mt-2">${r.notes || ''}</div></div><button ${active?'disabled':''} onclick="switchModel('${key}')" class="px-3 py-2 rounded-xl ${active?'bg-slate-700':'bg-emerald-600 hover:bg-emerald-500'}">${active?'当前使用中':'切换默认'}</button></div>`;
    routes.appendChild(card);
  }
  const fleet = document.getElementById('fleet');
  fleet.innerHTML='';
  for(const k of ['main','laifu','hk','lobster']){
    const n=data.fleet[k];
    const c = n.color==='green'?'bg-emerald-500':(n.color==='yellow'?'bg-yellow-400':'bg-slate-500');
    const card=document.createElement('div');
    card.className='rounded-2xl border border-slate-800 bg-slate-950 p-4';
    card.innerHTML=`<div class="flex items-center gap-3"><span class="w-3 h-3 rounded-full ${c} inline-block"></span><div class="font-semibold">${n.name}</div></div><div class="text-slate-400 text-sm mt-3">${n.detail}</div>`;
    fleet.appendChild(card);
  }
}
async function switchModel(modelKey){
  await fetch('/api/model/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({modelKey})});
  await loadState();
}
async function addRoute(){
  const payload={provider:provider.value,model:model.value,alias:alias.value,baseUrl:baseUrl.value,apiKey:apiKey.value,notes:notes.value,enabled:true};
  await fetch('/api/model/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  ['provider','model','alias','baseUrl','apiKey','notes'].forEach(id=>document.getElementById(id).value='');
  await loadState();
}
loadState();
setInterval(loadState, 5000);
</script></body></html>'''
    return HTMLResponse(html)
