"""框架与各实验模块独立检查，无云模型调用。TODO输出清单并退出2。"""
import argparse,asyncio,hashlib,importlib.metadata,json,os,platform,sys
from datetime import datetime,timezone
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from assessment import check_result,stage_status
from preflight import require_release
BASE=Path(__file__).resolve().parent


def value_of(response):
    value=response.structuredContent
    if value is None:value=json.loads(next(c.text for c in response.content if c.type=='text'))
    if isinstance(value,dict) and set(value)=={'result'}:value=value['result']
    return value


def cases(stage,advanced=False):
    p=os.getpid()
    jobs=[{'id':'A','arrival':0,'burst':4},{'id':'B','arrival':1,'burst':5},{'id':'C','arrival':2,'burst':1}]
    modules={
      'framework':[('get_time',{}),('get_memory_info',{})],
      'memory':[('get_memory_info',{}),('list_top_processes',{'limit':3}),
        ('get_process_memory',{'pid':p}),('sample_process_memory',{'pid':p,'samples':2,'interval':0.1}),
        ('analyze_memory_patterns',{'pages':[0,1,0,2]})]+[
        ('simulate_page_fault',{'algorithm':a,'frames':2,'pages':[0,1,0,2],'seed':42})
        for a in ['FIFO','LRU','CLOCK','OPT']+(['RANDOM','SECOND_CHANCE','HYBRID'] if advanced else [])],
      'filesystem':[('get_filesystem_info',{}),('analyze_file_distribution',{}),
        ('trace_file_access',{'seconds':0.6})]+[
        ('simulate_disk_allocation',{'strategy':s,'blocks':24}) for s in ['contiguous','linked','indexed']],
      'process':[('get_process_tree',{}),('monitor_context_switches',{'seconds':0.1}),
        ('monitor_context_switches',{'pid':p,'seconds':0.1}),('analyze_scheduling',{'seconds':0.1}),
        ('get_process_schedstat',{'pid':p,'seconds':0.1})]+[
        ('simulate_scheduler',{'algorithm':a,'quantum':2,'jobs':jobs})
        for a in ['FCFS','SJF','RR']+(['MLFQ'] if advanced else [])]}
    return sum((modules[m] for m in ['framework','memory','filesystem','process']),[]) if stage=='all' else modules[stage]


async def validate(require_openeuler=False,output=None,require_version=None,stage='framework',advanced=False):
    if hasattr(os,'geteuid') and os.geteuid()==0:raise RuntimeError('请用普通实验用户，不使用root')
    release=Path('/etc/os-release').read_text() if Path('/etc/os-release').exists() else ''
    if require_version:require_release(release,require_version);require_openeuler=True
    if require_openeuler and (platform.system()!='Linux' or 'openeuler' not in release.lower()):raise ValueError('非openEuler，不能作为目标云机验收')
    if sys.version_info<(3,10):raise ValueError('MCP需要Python>=3.10；目标固定3.11.16')
    from prepare_fixtures import prepare
    prepare()
    report=dict(started_at=datetime.now(timezone.utc).isoformat(),stage=stage,advanced=advanced,
        scope='openEuler_target' if require_openeuler else 'local_portable_not_cloud',
        platform=platform.platform(),python=sys.version,os_release=release,cloud_model_called=False,
        dependencies={x:importlib.metadata.version(x) for x in ['mcp','psutil','httpx','pydantic','jsonschema']},
        source_sha256={p.relative_to(BASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*.py') if '.venv' not in p.parts},
        tools=[],calls=[],module_tools={},success=False,status='failed')
    dest=Path(output) if output else BASE/'evidence'/f'{stage}-validation.json'
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','SECRET','TOKEN','PASSWORD'])}
    env['OSLAB_ROOT']=str(BASE/'lab-data')
    params=StdioServerParameters(command=sys.executable,args=[str(BASE/'server.py')],env=env)
    try:
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize();listed=await session.list_tools()
                report['tools']=[t.name for t in listed.tools]
                assert len(listed.tools)==16,'应发现16工具；发现不表示均已实现'
                dest.parent.mkdir(parents=True,exist_ok=True)
                (dest.parent/'tool_schema.json').write_text(json.dumps(listed.model_dump(mode='json'),ensure_ascii=False,indent=2))
                for name,args in cases(stage,advanced):
                    row=dict(tool=name,arguments=args,status='FAILED')
                    reader=None
                    if name=='trace_file_access' and platform.system()=='Linux':
                        async def read_fixture():
                            for _ in range(4):
                                await asyncio.sleep(.1)
                                (BASE/'lab-data'/'notes.txt').read_bytes()
                        reader=asyncio.create_task(read_fixture())
                    try:
                        response=await asyncio.wait_for(session.call_tool(name,args),20)
                        assert not response.isError,'MCP protocol/tool wrapper error'
                        value=value_of(response);row['result']=value;check_result(name,value)
                        if reader and value['ok']:
                            assert any('ACCESS' in e['events'] for e in value['data']['events']),'未捕获验证器在采样窗口内的受控读取'
                        row['status']='PASSED' if value['ok'] else value['error'] if value['error'] in {'NOT_IMPLEMENTED','UNSUPPORTED_PLATFORM'} else 'FAILED'
                    except Exception as exc:row['error']=str(exc)
                    finally:
                        if reader:await reader
                    report['calls'].append(row)
        if stage=='framework':
            for module,count in [('memory',7),('filesystem',5),('process',6)]:
                sub=StdioServerParameters(command=sys.executable,args=[str(BASE/'server.py'),'--module',module],env=env)
                async with stdio_client(sub) as (r,w):
                    async with ClientSession(r,w) as session:
                        await session.initialize();ls=await session.list_tools();assert len(ls.tools)==count
                        report['module_tools'][module]=[t.name for t in ls.tools]
        report['status']=stage_status(report['calls']);report['success']=report['status']=='passed'
    except Exception as exc:report['error']=str(exc)
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'stage':stage,'status':report['status'],'success':report['success'],
        'passed':sum(r['status']=='PASSED' for r in report['calls']),
        'pending':sorted({r.get('result',{}).get('task',r['tool']) for r in report['calls'] if r['status']=='NOT_IMPLEMENTED'}),
        'evidence':str(dest)},ensure_ascii=False))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['framework','memory','filesystem','process','all'],default='framework')
    p.add_argument('--advanced',action='store_true');p.add_argument('--require-openeuler',action='store_true')
    p.add_argument('--require-version');p.add_argument('--output');a=p.parse_args()
    try:
        report=asyncio.run(validate(a.require_openeuler,a.output,a.require_version,a.stage,a.advanced))
        sys.exit(0 if report['success'] else 2 if report['status']=='not_implemented' else 1)
    except Exception as exc:print(f'检查未完成：{exc}',file=sys.stderr);sys.exit(1)
