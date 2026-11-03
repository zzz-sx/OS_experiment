"""仅监听127.0.0.1的自然语言前端。默认模拟模型；--cloud才请求MaaS。"""
import argparse
import asyncio
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import host

PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>openEuler 实验助手</title><style>body{font:18px system-ui;max-width:980px;margin:3rem auto;padding:0 1rem;background:#f4f7f8;color:#173743}textarea{width:100%;box-sizing:border-box;min-height:120px;padding:1rem;font:inherit}button{margin:1rem 0;padding:.7rem 1.4rem;font:inherit;background:#007a80;color:white;border:0;border-radius:6px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:1rem}summary{cursor:pointer}</style>
<h1>openEuler 操作系统实验助手</h1><p id="mode"></p><p>问题 → 模型选择工具 → MCP采集或模拟 → 依据证据解释。每次提交是独立任务。PID请先查询，不输入密码或密钥。</p>
<p>学生框架版：先用已提供的内存快照验证链路。其余OS接口返回NOT_IMPLEMENTED时，请完成students目录任务。</p>
<textarea id="q">查询当前内存快照并说明采样局限。</textarea><br><button id="go">运行一次</button><p id="status"></p><h2>解释</h2><pre id="answer">等待输入</pre><details><summary>查看工具证据与调用记录</summary><pre id="trace"></pre></details>
<script>fetch('/mode').then(r=>r.json()).then(d=>{document.getElementById('mode').textContent=d.message});
document.getElementById('go').onclick=async()=>{const b=document.getElementById('go');b.disabled=true;document.getElementById('status').textContent='处理中，请勿重复提交';try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:document.getElementById('q').value})});const d=await r.json();document.getElementById('answer').textContent=d.answer||d.error||'';document.getElementById('trace').textContent=JSON.stringify(d.trace||[],null,2);document.getElementById('status').textContent='状态：'+(d.status||r.status)+'；模型请求：'+(d.model_requests||0)+'；证据：'+(d.evidence_file||'无')}catch(e){document.getElementById('status').textContent='网络中断：不要自动重试，先检查本地证据和用量'}finally{b.disabled=false}};</script></html>'''


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cloud',action='store_true'); ap.add_argument('--port',type=int,default=8765); ap.add_argument('--config')
    args=ap.parse_args()
    if not 1024<=args.port<=65535: raise SystemExit('port: 1024..65535')
    cfg=json.loads((Path(args.config) if args.config else host.BASE/'config.example.json').read_text()); host.validate_config(cfg)
    if args.cloud and not host.os.environ.get('MAAS_API_KEY'): raise SystemExit('先在当前终端环境配置 MAAS_API_KEY')
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*unused): pass # Do not log prompts.
        def send(self,value,status=200,html=False):
            b=value.encode() if html else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
        def valid_host(self): return self.headers.get('Host') in {f'127.0.0.1:{args.port}',f'localhost:{args.port}'}
        def do_GET(self):
            if not self.valid_host(): return self.send({'error':'invalid host'},403)
            if self.path=='/': return self.send(PAGE,html=True)
            if self.path=='/mode': return self.send({'message':('真实华为云模型；共用持久预算账本，可能计费。' if args.cloud else '离线模型模拟；真实MCP调用，不产生模型费用。')+f'当前目录模型请求总上限{cfg["max_total_requests"]}次；本地估算预算{cfg["budget_cny"]}元。'})
            self.send({'error':'not found'},404)
        def do_POST(self):
            if not self.valid_host() or self.headers.get('Origin') not in {f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'}:
                return self.send({'error':'origin rejected'},403)
            if self.path!='/ask' or self.headers.get('Content-Type')!='application/json': return self.send({'error':'invalid request'},400)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 1<=n<=20000: raise ValueError('request too large')
                data=json.loads(self.rfile.read(n)); question=data['question']
                if not isinstance(question,str) or not 1<=len(question.strip())<=4000: raise ValueError('question: 1..4000 chars')
            except (ValueError,KeyError,TypeError): return self.send({'error':'invalid question'},400)
            if not lock.acquire(blocking=False): return self.send({'error':'另一个任务正在运行，请等候'},429)
            out=host.BASE/'evidence'/('web-'+uuid.uuid4().hex+'.json')
            try:
                try: report=asyncio.run(host.run(question,mock=not args.cloud,config_path=args.config,output=str(out)))
                except Exception:
                    report=json.loads(out.read_text()) if out.exists() else {'status':'failed','error':'初始化失败，检查终端信息'}
                report['evidence_file']=out.name; self.send(report)
            finally: lock.release()
    httpd=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'http://127.0.0.1:{args.port}  mode={"cloud" if args.cloud else "mock"}; Ctrl+C停止；不开放公网端口')
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()


if __name__=='__main__': main()
