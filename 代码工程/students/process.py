"""进程与调度实验。采集逻辑由学生实现，权限及参数边界已提供。"""
import os,platform,time
from pathlib import Path
from lab_common import result,own_process,integer,duration,psutil
from students.algorithms import JOBS,scheduler


def _sample_delta(read,seconds):
    before=read();start=time.monotonic()
    time.sleep(seconds)
    after=read();elapsed=time.monotonic()-start
    delta=[new-old for old,new in zip(before,after)]
    if min(delta)<0:raise ValueError('sample counter decreased')
    return elapsed,delta


def _check_alive(proc):
    # psutil.is_running会核对创建时间，识别同一PID已被复用。
    if not proc.is_running() or proc.status()==psutil.STATUS_ZOMBIE:
        raise psutil.NoSuchProcess(proc.pid,msg='process exited or PID reused')


def get_process_tree(limit=50) -> dict:
    """【P1】构造当前真实UID可见进程的父子关系，最多100项。

    data={'nodes':[{'pid':int,'ppid':int,'name':str}], 'omitted':int}。
    以PID/PPID边表示树/森林；父节点可能在用户范围外，不能伪造根进程。
    进程在遍历时可能退出或权限拒绝；快照并不原子，记录遗漏和局限。
    不返回完整命令行、环境或其他用户进程。
    """
    integer(limit,1,100,'limit')
    if not hasattr(os,'getuid'):
        return result('psutil.process_iter',error='UNSUPPORTED_PLATFORM')
    uid=os.getuid();nodes=[];omitted=0
    for proc in psutil.process_iter():
        try:
            if proc.uids().real==uid:
                nodes.append(dict(pid=proc.pid,ppid=proc.ppid(),name=proc.name()))
        except (psutil.NoSuchProcess,psutil.AccessDenied):omitted+=1
    nodes.sort(key=lambda node:node['pid'])
    return result('psutil.process_iter',dict(nodes=nodes[:limit],omitted=omitted+max(0,len(nodes)-limit)),
                  units={'nodes':'count'},limitations=['仅当前真实UID；父进程可在结果之外，未补造根节点。',
                      '动态快照不是原子操作；omitted含读取失败及超出上限的项。'])


def monitor_context_switches(pid=None,seconds=1) -> dict:
    """【P2】测量采样窗口内的上下文切换计数差与频率。

    无pid：系统全局；data含elapsed_seconds、delta、rate_per_second。
    有pid：同用户进程；delta和rate_per_second按voluntary/involuntary分项。
    频率用实际monotonic区间，不直接用请求秒数；单位count与count/s。
    校验进程退出、PID复用或计数回退，不能返回负数并解释成性能提升。
    不由计数估计单次切换耗时、缓存代价或调度延迟。
    """
    duration(seconds,0.1,5)
    if pid is None:
        elapsed,(delta,)=_sample_delta(lambda:(psutil.cpu_stats().ctx_switches,),seconds)
        rate=delta/elapsed;source='psutil.cpu_stats'
    else:
        proc=own_process(pid)
        elapsed,counts=_sample_delta(proc.num_ctx_switches,seconds)
        _check_alive(proc)
        delta=dict(zip(('voluntary','involuntary'),counts))
        rate={key:value/elapsed for key,value in delta.items()};source='psutil.Process.num_ctx_switches'
    return result(source,dict(pid=pid,elapsed_seconds=elapsed,delta=delta,rate_per_second=rate),
                  units={'delta':'count','rate':'count/s','elapsed':'seconds'},
                  limitations=['变化率按实际单调时钟窗口计算，不能推出单次切换耗时、缓存代价或调度延迟。'])


def parse_cpu(line: str) -> list[int]:
    """【P3a】解析/proc/stat总cpu行的前8项整数计数。

    顺序user,nice,system,idle,iowait,irq,softirq,steal；输入不完整应报错。
    guest/guest_nice已包含在其他字段中，不再累加。可用人工短行独立测试。
    """
    fields=line.split()
    if len(fields)<9 or fields[0]!='cpu':raise ValueError('expected aggregate cpu line with 8 counters')
    return [int(value) for value in fields[1:9]]


def analyze_scheduling(seconds=1) -> dict:
    """【P3】Linux区间CPU时间比例，平台不支持应返回明确错误。

    读两次/proc/stat总cpu行，调用自己的parse_cpu，保留raw_delta_ticks及total_ticks。
    data加elapsed_seconds和user_percent(含nice)、system_percent(含irq/softirq)、
    idle_percent、iowait_percent、steal_percent；有效样本比例和约100。
    计数回退或零总量应报错。iowait解释有局限，比例不能证明调度策略或延迟。
    """
    duration(seconds,0.1,5)
    source='/proc/stat (aggregate cpu)'
    if platform.system()!='Linux':return result(source,error='UNSUPPORTED_PLATFORM')

    def read():
        with open('/proc/stat') as stream:return parse_cpu(stream.readline())

    elapsed,ticks=_sample_delta(read,seconds)
    total=sum(ticks)
    if total==0:raise ValueError('no CPU ticks in sample')
    user,nice,system,idle,iowait,irq,softirq,steal=ticks
    return result(source,dict(elapsed_seconds=elapsed,raw_delta_ticks=ticks,total_ticks=total,
        user_percent=100*(user+nice)/total,system_percent=100*(system+irq+softirq)/total,
        idle_percent=100*idle/total,iowait_percent=100*iowait/total,steal_percent=100*steal/total),
        units={'raw_delta_ticks':'ticks','percent':'percent','elapsed':'seconds'},
        limitations=['汇总所有CPU；guest时间已计入原字段。iowait不能直接解释为进程等待，比例不能证明调度策略或延迟。'])


def get_process_schedstat(pid,seconds=0.2) -> dict:
    """【P4】读取同用户/proc/PID/schedstat的两次区间差。

    data含pid、elapsed_seconds、runtime_ns、runqueue_wait_ns、timeslices、
    schedstats_enabled、mean_runqueue_wait_ns。纳秒计数与timeslice次数分别标单位。
    只有统计明确启用且timeslices差>0才算均值；禁用/未知/无有效样本时为None。
    不启用内核参数，不把None解释为零延迟。检查退出、PID复用与计数回退。
    """
    duration(seconds,0.1,5);source='/proc/PID/schedstat'
    if platform.system()!='Linux':return result(source,error='UNSUPPORTED_PLATFORM')
    proc=own_process(pid);path=Path('/proc')/str(pid)/'schedstat'
    elapsed,(runtime,waiting,timeslices)=_sample_delta(lambda:list(map(int,path.read_text().split())),seconds)
    _check_alive(proc)
    try:enabled=int(Path('/proc/sys/kernel/sched_schedstats').read_text())
    except (FileNotFoundError,PermissionError):enabled=None
    return result(source,dict(pid=pid,elapsed_seconds=elapsed,runtime_ns=runtime,
        runqueue_wait_ns=waiting,timeslices=timeslices,schedstats_enabled=enabled,
        mean_runqueue_wait_ns=waiting/timeslices if enabled==1 and timeslices else None),
        units={'runtime':'ns','runqueue_wait':'ns','mean_runqueue_wait':'ns','timeslices':'count','elapsed':'seconds'},
        limitations=['仅统计已启用且有时间片时计算平均值；null不代表零延迟，未修改内核设置。'])


def simulate_scheduler(algorithm='RR',quantum=2,jobs=None,boost_interval=20) -> dict:
    """【已提供调用框架】学生实现A2后，由此返回教学模拟；不会修改内核调度。"""
    return result('students.algorithms.scheduler',
                  scheduler(JOBS if jobs is None else jobs,algorithm,quantum,boost_interval),
                  kind='simulation',units={'time':'abstract time units'})
