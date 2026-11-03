"""不调用云模型，单独发现/调用 MCP 工具。"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    p=argparse.ArgumentParser()
    p.add_argument('tool',nargs='?',default='get_time')
    p.add_argument('--args',default='{}')
    p.add_argument('--list',action='store_true')
    p.add_argument('--unwrap',action='store_true',help='仅打印工具内层JSON；待实现退出2')
    p.add_argument('--module',choices=['all','memory','filesystem','process'],default='all')
    a=p.parse_args()
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','SECRET','TOKEN','PASSWORD'])}
    async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name('server.py')),'--module',a.module],env=env)) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            if a.list:
                out=(await s.list_tools()).model_dump(mode='json')
                code=0
            else:
                response=await asyncio.wait_for(s.call_tool(a.tool,json.loads(a.args)),20)
                out=response.model_dump(mode='json')
                if response.isError:code=1
                else:
                    from validate_lab import value_of
                    value=value_of(response)
                    code=0 if value.get('ok') else 2 if value.get('error')=='NOT_IMPLEMENTED' else 3
                    if a.unwrap:out=value
            print(json.dumps(out,ensure_ascii=False,indent=2))
            return code

if __name__=='__main__':
    sys.exit(asyncio.run(main()))
