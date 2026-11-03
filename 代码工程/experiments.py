"""已提供对照编排与留证；实际计算委托学生算法，TODO不伪造图表。"""
import argparse,csv,html,json,os,platform,sys
from datetime import datetime,timezone
from pathlib import Path
from students.algorithms import REFERENCE,JOBS,page_replace,scheduler,disk_allocate
from lab_common import StudentTaskPending


def collect(module='all',advanced=False):
    records=[]
    def attempt(name,args,fn,*pos):
        row=dict(experiment=name,parameters=args,kind='simulation',status='FAILED')
        try:row['data']=fn(*pos);row['status']='COMPLETED'
        except StudentTaskPending as exc:row.update(status='NOT_IMPLEMENTED',task=exc.task,error=str(exc))
        except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'
        records.append(row)
    if module in {'all','memory'}:
        for frames in [2,3]:
            for algorithm in ['FIFO','LRU','CLOCK','OPT']+(['RANDOM','SECOND_CHANCE','HYBRID'] if advanced else []):
                attempt('page_replacement',dict(frames=frames,algorithm=algorithm,pages=REFERENCE,seed=42),page_replace,REFERENCE,frames,algorithm,42)
    if module in {'all','filesystem'}:
        for blocks in [24,32]:
            for strategy in ['contiguous','linked','indexed']:
                attempt('disk_allocation',dict(blocks=blocks,strategy=strategy),disk_allocate,strategy,blocks)
    if module in {'all','process'}:
        for quantum in [1,2]:
            for algorithm in ['FCFS','SJF','RR']+(['MLFQ'] if advanced else []):
                attempt('scheduler',dict(algorithm=algorithm,quantum=quantum,jobs=JOBS),scheduler,JOBS,algorithm,quantum,20)
        if advanced:
            for boost in [0,10,20]:
                attempt('mlfq_boost',dict(boost_interval=boost,jobs=JOBS),scheduler,JOBS,'MLFQ',2,boost)
    return records


def controlled_observations():
    # 先确认采样功能可用，避免尚未完成时无意义地启动工作负载。
    import os_tools as ops
    if platform.system()!='Linux' or os.geteuid()==0:return {'status':'UNSUPPORTED_ENVIRONMENT','kind':'controlled_workload'}
    try:
        for value in [ops.sample_process_memory(os.getpid(),2,.1),ops.monitor_context_switches(os.getpid(),.1),ops.analyze_scheduling(.1)]:
            if not value['ok']:return {'status':'FAILED_PRECHECK','result':value,'kind':'controlled_workload'}
        from controlled_runner import controlled
        return {'status':'COMPLETED','kind':'controlled_workload','cases':controlled()}
    except StudentTaskPending as exc:return {'status':'NOT_IMPLEMENTED','task':exc.task,'error':str(exc),'kind':'controlled_workload'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--module',choices=['all','memory','filesystem','process'],default='all')
    p.add_argument('--advanced',action='store_true');p.add_argument('--controlled',action='store_true')
    p.add_argument('--output',default='evidence/experiments');args=p.parse_args()
    records=collect(args.module,args.advanced)
    controlled=controlled_observations() if args.controlled else {'status':'NOT_REQUESTED','kind':'controlled_workload'}
    done=all(r['status']=='COMPLETED' for r in records) and (not args.controlled or controlled['status']=='COMPLETED')
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),module=args.module,completed=done,
        cloud_model_called=False,comparisons=records,controlled_observations=controlled)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (output/'summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['experiment','parameters','status','data_or_error'])
        for r in records:w.writerow([r['experiment'],json.dumps(r['parameters']),r['status'],json.dumps(r.get('data',r.get('error')),ensure_ascii=False)])
    body=''.join('<h2>'+html.escape(r['experiment'])+' '+html.escape(r['status'])+'</h2><pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre>' for r in records)
    (output/'results.html').write_text('<!doctype html><meta charset="utf-8"><title>个人实验对照</title><style>body{font:17px system-ui;max-width:1000px;margin:2rem auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef4f4;padding:1rem}</style><h1>个人实验对照</h1><p>NOT_IMPLEMENTED表示待实现，无成功数值或图表。模拟与受控观测分开保存。</p>'+body)
    print(json.dumps({'completed':done,'pending_cases':sum(r['status']=='NOT_IMPLEMENTED' for r in records),'output':str(output),'cloud_model_called':False},ensure_ascii=False))
    return 0 if done else 2


if __name__=='__main__':sys.exit(main())
