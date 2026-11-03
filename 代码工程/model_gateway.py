"""已提供：模型API、持久用量限额与离线模型适配。无需学生重新实现。"""
import json,math,os,sqlite3,sys
from datetime import datetime
from pathlib import Path
import httpx
BASE=Path(__file__).resolve().parent

def encode(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))

def provider_of(config):
    return config.get('provider','huawei')

def api_key_env(config):
    return 'DEEPSEEK_API_KEY' if provider_of(config)=='deepseek' else 'MAAS_API_KEY'

def deadline_of(config):
    return datetime.fromisoformat(config.get('requests_valid_until',config.get('coupon_expires_at','')))

def validate_config(config):
    profiles={'huawei':('https://api.modelarts-maas.com/v2/chat/completions','openpangu-2.0-flash'),
              'deepseek':('https://api.deepseek.com/chat/completions','deepseek-flash')}
    if provider_of(config) not in profiles or (config.get('endpoint'),config.get('model'))!=profiles[provider_of(config)]:
        raise ValueError('endpoint/model must match the selected official provider profile')
    if provider_of(config)=='deepseek':
        return
    for key,cap in [('max_rounds',6),('max_tool_calls',24),('max_calls_per_round',4),('max_requests_per_run',6),
                    ('max_total_requests',100),('max_output_tokens',2400),('max_request_bytes',120000),('max_tool_result_bytes',64000)]:
        value=config.get(key,100 if key=='max_total_requests' else None)
        if type(value) is not int or not 1<=value<=cap: raise ValueError(f'{key}: integer 1..{cap}')
    for key in ['budget_cny','per_request_reserve_cny','input_cny_per_million','output_cny_per_million']:
        v=config[key]
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0: raise ValueError(f'{key}: positive finite number')
    if config['budget_cny']>5: raise ValueError('teaching local budget cap: 5 CNY')
    min_input,min_output=(2.0,8.0) if provider_of(config)=='deepseek' else (0.8,1.6)
    if config['input_cny_per_million']<min_input or config['output_cny_per_million']<min_output:
        raise ValueError('configured rates below conservative uncached provider rates')
    estimated_max=(config['max_request_bytes']*config['input_cny_per_million']+config['max_output_tokens']*config['output_cny_per_million'])/1000000
    if config['per_request_reserve_cny']<estimated_max: raise ValueError('reservation too small for configured request limits')
    # Byte-based input estimate is deliberately conservative, not a billing guarantee.
    expiry=deadline_of(config)
    if expiry.tzinfo is None: raise ValueError('coupon expiry requires timezone')

class BudgetLedger:
    """同一数据库文件内的请求预留。不是华为云账户级自动停费。"""
    def __init__(self,path,config):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.db = sqlite3.connect(path,timeout=5)
        self.db.execute('CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY, amount REAL, status TEXT, created TEXT)')
        self.db.commit()
        self.config = config

    def reserve(self):
        if datetime.now().astimezone() >= deadline_of(self.config):
            raise RuntimeError('配置的请求有效期已结束，程序停止发起付费请求。')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            used = self.db.execute('SELECT COALESCE(SUM(amount),0) FROM calls').fetchone()[0]
            count = self.db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
            if count >= self.config.get('max_total_requests',100):
                raise RuntimeError('累计模型请求达到上限，不可通过重启程序重置。')
            amount = self.config['per_request_reserve_cny']
            if used+amount > self.config['budget_cny']:
                raise RuntimeError('本地实验预算不足，已停止。检查账单后再调整预算。')
            row = self.db.execute('INSERT INTO calls(amount,status,created) VALUES (?,?,?)',
                                  (amount,'reserved',datetime.now().astimezone().isoformat()))
            self.db.commit()
            return row.lastrowid
        except Exception:
            self.db.rollback()
            raise

    def settle(self,ident,usage):
        if not isinstance(usage,dict) or not all(type(usage.get(k)) is int and usage[k]>=0 for k in ['prompt_tokens','completion_tokens']):
            # A timeout, a broken response or missing usage keeps its reservation.
            return None
        cost = (usage['prompt_tokens']*self.config['input_cny_per_million']+
                usage['completion_tokens']*self.config['output_cny_per_million'])/1_000_000
        self.db.execute('UPDATE calls SET amount=?,status=? WHERE id=?',(cost,'estimated',ident))
        self.db.commit()
        return cost

class Model:
    def __init__(self,config,mock=False):
        validate_config(config)
        self.config,self.mock,self.calls = config,mock,0
        self.usage_log = []
        self.ledger = None if mock or provider_of(config)=='deepseek' else BudgetLedger(BASE/'state'/'budget.sqlite',config)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(90,connect=10),follow_redirects=False)

    async def request(self,payload):
        if provider_of(self.config)!='deepseek' and self.calls >= self.config['max_requests_per_run']:
            raise RuntimeError('模型请求次数达到上限。')
        if len(encode(payload).encode()) > self.config['max_request_bytes']:
            raise RuntimeError('请求正文过大，请缩小问题或工具返回量。')
        if self.mock:
            self.calls += 1
            # Only the LLM responses are scripted. MCP communication and tools are real.
            if self.calls == 1 and self.config.get('mock_scenario') == 'pending':
                return {'choices':[{'message':{'role':'assistant','content':'','tool_calls':[
                    {'id':'pending_time','type':'function','function':{'name':'get_time','arguments':'{}'}},
                    {'id':'pending_tree','type':'function','function':{'name':'get_process_tree','arguments':'{}'}}]}}], 'usage':{}}
            if self.calls == 1:
                return {'choices':[{'message':{'role':'assistant','content':'', 'tool_calls':[
                    {'id':'demo_mem','type':'function','function':{'name':'get_memory_info','arguments':'{}'}},
                    {'id':'demo_time','type':'function','function':{'name':'get_time','arguments':'{}'}}]}}], 'usage':{}}
            evidence = [json.loads(x['content']) for x in payload['messages'] if x['role']=='tool']
            answer = '【离线模型模拟，非云端推理】\n已收到真实MCP工具返回；仅演示协议闭环，请核对每个结果的ok/error。\n'+encode(evidence)
            return {'choices':[{'message':{'role':'assistant','content':answer}}], 'usage':{}}
        key=os.environ.get(api_key_env(self.config),'').strip()
        if not key:
            raise ValueError(api_key_env(self.config)+' is not configured')
        ident = self.ledger.reserve() if self.ledger else None
        self.calls += 1
        try:
            response = await self.client.post(self.config['endpoint'],headers={
                'Authorization':'Bearer '+key, 'Content-Type':'application/json'},json=payload)
        except httpx.TimeoutException:
            raise RuntimeError('模型请求超时，请稍后重试。') from None
        if response.status_code != 200:
            detail = response.text.replace(key,'[REDACTED]')[:800]
            raise RuntimeError(f'模型接口 HTTP {response.status_code}: {detail}')
        body = response.json()
        cost = self.ledger.settle(ident,body.get('usage')) if self.ledger else None
        self.usage_log.append(dict(request=self.calls,usage=body.get('usage'),estimated_cny=cost))
        return body

    async def close(self):
        await self.client.aclose()
        if self.ledger:
            self.ledger.db.close()
