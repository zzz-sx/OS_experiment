"""已提供：限时负载编排与子进程回收，采样委托学生接口。"""
import os,platform,subprocess,sys
from pathlib import Path
import os_tools as ops
BASE=Path(__file__).resolve().parent

def controlled():
    if platform.system()!='Linux' or os.geteuid()==0: raise RuntimeError('受控负载只在隔离Linux普通实验用户下运行')
    records=[]
    for mode,count in [('sleep',1),('cpu',1),('sleep',2),('cpu',2),('memory',1)]:
        children=[]
        before=ops.get_memory_info()
        try:
            for _ in range(count):
                p=subprocess.Popen([sys.executable,str(BASE/'workload.py'),'--mode',mode,'--seconds','3','--mib','16'],stdout=subprocess.PIPE,text=True)
                children.append(p)
                line=p.stdout.readline()
                if not line.startswith('PID='): raise RuntimeError('workload failed before start')
            observed=[ops.monitor_context_switches(p.pid,.15) for p in children]
            sampled=[ops.sample_process_memory(p.pid,2,.1) for p in children]
            cpu=ops.analyze_scheduling(.2)
            during=ops.get_memory_info()
        finally:
            for p in children:
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.terminate()
                    try: p.wait(timeout=2)
                    except subprocess.TimeoutExpired: p.kill(); p.wait()
                if p.stdout: p.stdout.close()
        records.append(dict(kind='controlled_workload',mode=mode,process_count=count,max_memory_mib=16 if mode=='memory' else 0,
                            before=before,during=during,after=ops.get_memory_info(),process_switches=observed,process_memory=sampled,cpu=cpu,
                            limitations=['Different runs share the host; do not attribute all system-wide changes to the workload. No swap-exhaustion experiment. Per-switch time/cache cost is not measured.']))
    return records
