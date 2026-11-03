"""内存实验：真实进程观测与显式页面引用序列分析。"""
import os,platform,re,time
from datetime import datetime,timezone
from pathlib import Path
from lab_common import psutil,result,own_process,integer,duration
from students.algorithms import REFERENCE,page_replace

SMAPS_HEADER=re.compile(r'^([0-9a-fA-F]+-[0-9a-fA-F]+)[ \t]+([r-][w-][x-][ps])[ \t]+\S+[ \t]+\S+[ \t]+\d+(?:[ \t]+(.*))?$',re.MULTILINE)


def _check_identity(proc,created):
    if not proc.is_running() or proc.status()==psutil.STATUS_ZOMBIE or own_process(proc.pid).create_time()!=created:
        raise psutil.NoSuchProcess(proc.pid,msg='process exited or PID reused')


def get_memory_info() -> dict:
    """【已提供示例】真实内存快照，展示采集、单位和局限的统一写法。

    请据此实现其他接口，勿由一次快照推断局部性或抖动。
    该函数在内存任务中仅用作环境基线，不计作学生独立实现。
    """
    vm,swap=psutil.virtual_memory(),psutil.swap_memory()
    data={k:getattr(vm,k) for k in ['total','available','used','free','percent']}
    data['swap']=swap._asdict()
    return result('psutil.virtual_memory / swap_memory',data,
                  units={'memory':'bytes','percent':'percent'},limitations=[
                      'available是估计值；一次快照不足以证明抖动。',
                      'swap.total=0表示未配置可用交换区，不能据此断言无缺页。'])


def list_top_processes(limit: int=5) -> dict:
    """【M1】列出同用户进程中RSS最高的limit项。

    输入：limit为1..10，基本参数校验已提供。
    输出：result(...,data={'processes':[{'pid':int,'ppid':int,'name':str,
        'rss':int}], 'excluded':int},units={'rss':'bytes'})，kind=observation。
    行为：只统计当前真实UID；RSS降序；少于limit时返回全部实际项。
    边界：遍历时进程可退出或拒绝访问，跳过并记录excluded；不能伪造PID。
    提示：查看psutil.process_iter，避免向模型发送命令行或环境中的秘密。
    """
    integer(limit,1,10,'limit')
    if not hasattr(os,'getuid'):
        return result('psutil.process_iter',error='UNSUPPORTED_PLATFORM')
    rows=[];excluded=0
    for proc in psutil.process_iter():
        try:
            if proc.uids().real!=os.getuid():
                excluded+=1;continue
            created=proc.create_time()
            row=dict(pid=proc.pid,ppid=proc.ppid(),name=proc.name(),rss=proc.memory_info().rss)
            _check_identity(proc,created)
            rows.append(row)
        except (psutil.Error,OSError):excluded+=1
    rows.sort(key=lambda row:(-row['rss'],row['pid']))
    return result('psutil.process_iter / Process.memory_info',
                  dict(processes=rows[:limit],excluded=excluded),units={'rss':'bytes'},
                  limitations=['仅当前真实UID；excluded含其他UID及读取失败的进程；动态快照不是原子操作。',
                               'RSS可能重复计入共享页，不能相加当作独占物理内存。'])


def parse_smaps(text: str,limit: int=12) -> list:
    """【M2a】将给定的Linux smaps文本解析为最多limit个映射。

    返回list[dict]，每项含address、permissions、label及实际存在的
    Size_KiB、Rss_KiB、Pss_KiB、Private_Dirty_KiB。值按KiB保留，缺字段不补0。
    处理多映射、匿名段、空输入、不含PSS的记录及最后一段。
    label仅保留文件基名或[heap]一类标签，不泄露完整文件路径。
    这是纯解析函数，可在任意平台用人工短文本独立测试。
    """
    integer(limit,1,20,'limit')
    rows=[];current=None
    fields={'Size','Rss','Pss','Private_Dirty'}
    for line in text.splitlines():
        header=SMAPS_HEADER.fullmatch(line)
        if header:
            if len(rows)>=limit:break
            address,permissions,label=header.groups()
            label=label or '[anonymous]'
            current=dict(address=address,permissions=permissions,
                         label=label if label.startswith('[') else label.rsplit('/',1)[-1])
            rows.append(current)
        elif current is not None:
            parts=line.split()
            if parts and parts[0].rstrip(':') in fields:
                if len(parts)!=3 or parts[2]!='kB':raise ValueError('invalid smaps KiB field')
                value=int(parts[1])
                if value<0:raise ValueError('negative smaps counter')
                current[parts[0].rstrip(':')+'_KiB']=value
    return rows


def get_process_memory(pid: int,max_maps: int=12) -> dict:
    """【M2】读取同用户进程RSS与有界smaps映射。

    own_process权限检查已提供。输出data含pid、name、memory(psutil字节字段)、
    maps(parse_smaps结果)、maps_partial。读取文本最多2,000,000字节，映射最多20。
    Linux读/proc/PID/smaps；其他平台可保留psutil项并声明maps不可用。
    RSS可能重复计入共享页，不能等同私有物理内存；一次映射列表可不完整。
    若进程退出/权限拒绝，让异常交给Server返回错误，勿返回成功的零值。
    """
    integer(max_maps,1,20,'max_maps');proc=own_process(pid)
    created=proc.create_time()
    data=dict(pid=pid,name=proc.name(),memory=proc.memory_info()._asdict(),maps=[],maps_partial=True)
    limitations=['RSS包含共享页；映射与RSS不是原子快照，映射单位KiB，memory单位bytes。']
    if platform.system()=='Linux':
        with (Path('/proc')/str(pid)/'smaps').open('rb') as stream:
            raw=stream.read(2_000_000)
        text=raw.decode('utf-8',errors='replace')
        headers=list(SMAPS_HEADER.finditer(text))
        clipped=len(raw)==2_000_000
        if clipped:
            # 最后一段可能只有部分指标，整个丢弃，不把截断记录当完整映射。
            text=text[:headers[-1].start()] if headers else ''
        data['maps']=parse_smaps(text,max_maps)
        data['maps_partial']=clipped or len(headers)>max_maps
        if data['maps_partial']:limitations.append('达到映射数量或读取字节上限，maps仅为部分结果。')
    else:limitations.append('非Linux平台，smaps不可用；仅保留psutil内存字段。')
    _check_identity(proc,created)
    return result('psutil.Process.memory_info / /proc/PID/smaps',data,
                  units={'memory':'bytes','maps':'KiB'},limitations=limitations)


def analyze_memory_patterns(pages: list[int]|None=None) -> dict:
    """【M3】分析显式引用序列的复用与相邻页号代理指标。

    None使用REFERENCE。1..128项，每项0..4095的整数，禁止bool。
    输出data：length、distinct_pages、repeated_references、mean_reuse_interval、
    adjacent_page_ratio。复用间隔定义为同页相邻两次出现的索引之差；无复用为None。
    相邻比例定义为相邻访问中abs(页号差)<=1的比例；单项序列定义为0。
    kind=simulation；单位分别为references与fraction。
    结果仅描述输入序列，不能由此认定当前真实程序的时间/空间局部性。
    """
    pages=REFERENCE if pages is None else pages
    if not isinstance(pages,list) or not 1<=len(pages)<=128:raise ValueError('pages: list of 1..128 integers')
    last={};intervals=[]
    for index,page in enumerate(pages):
        integer(page,0,4095,'page')
        if page in last:intervals.append(index-last[page])
        last[page]=index
    adjacent=sum(abs(a-b)<=1 for a,b in zip(pages,pages[1:]))
    return result('explicit page reference sequence',dict(
        length=len(pages),distinct_pages=len(last),repeated_references=len(intervals),
        mean_reuse_interval=sum(intervals)/len(intervals) if intervals else None,
        adjacent_page_ratio=adjacent/(len(pages)-1) if len(pages)>1 else 0),
        kind='simulation',units={'reuse_interval':'references','adjacent_page_ratio':'fraction'},
        limitations=['只描述输入序列的复用及相邻页号代理指标，不能证明真实程序局部性或抖动。'])


def simulate_page_fault(algorithm='FIFO',frames=3,pages=None,seed=42) -> dict:
    """【已提供调用框架】计算逻辑位于students/algorithms.py的A1。

    完成page_replace后本接口即可调用；未实现异常由Server变成NOT_IMPLEMENTED。
    """
    return result('students.algorithms.page_replace',
                  page_replace(REFERENCE if pages is None else pages,frames,algorithm,seed),
                  kind='simulation',units={'fault_rate':'fraction','faults':'count'})


def read_proc_faults(pid: int) -> dict:
    """【M4a】解析/proc/PID/stat中的minor_faults、major_faults累计计数。

    输出{'minor_faults':int,'major_faults':int}。comm名称可含空格及括号，不能对
    整行直接split后用固定下标。调用者负责同用户检查；本函数不改内核计数。
    可自行另写纯文本解析函数，用包含特殊comm的短样本验证字段位置。
    """
    text=(Path('/proc')/str(pid)/'stat').read_text()
    closing=text.rfind(')')
    if closing<0:raise ValueError('invalid /proc/PID/stat comm')
    fields=text[closing+1:].split()
    if len(fields)<10:raise ValueError('incomplete /proc/PID/stat')
    # fields[0]为第3字段state；minflt/majflt为第10/12字段，不含子进程计数。
    minor,major=int(fields[7]),int(fields[9])
    if min(minor,major)<0:raise ValueError('negative fault counter')
    return dict(minor_faults=minor,major_faults=major)


def sample_process_memory(pid: int,samples=3,interval=0.2) -> dict:
    """【M4】对同用户存活进程做有界时间序列采样。

    samples=2..10、interval=0.1..0.5秒。保留创建时间以识别PID复用。
    data含pid、samples(list)、delta(dict)。每行有sampled_at、monotonic_seconds、
    rss_bytes、system_swap_in_bytes、system_swap_out_bytes，Linux加minor/major_faults。
    delta为末项减首项；两种时钟用途不同，实际间隔需保留。不可无限采样。
    全局swap差不等于该进程IO；minor/major fault、RSS变化和抖动须区分。
    """
    integer(samples,2,10,'samples');duration(interval,0.1,0.5);proc=own_process(pid)
    created=proc.create_time();rows=[]
    linux=platform.system()=='Linux'
    counters=['system_swap_in_bytes','system_swap_out_bytes']+(['minor_faults','major_faults'] if linux else [])
    for index in range(samples):
        if index:time.sleep(interval)
        _check_identity(proc,created)
        rss=proc.memory_info().rss;swap=psutil.swap_memory()
        faults=read_proc_faults(pid) if linux else {}
        _check_identity(proc,created)
        row=dict(sampled_at=datetime.now(timezone.utc).isoformat(),monotonic_seconds=time.monotonic(),
                 rss_bytes=rss,system_swap_in_bytes=swap.sin,system_swap_out_bytes=swap.sout,**faults)
        if rows and any(row[key]<rows[-1][key] for key in counters):raise ValueError('sample counter decreased')
        rows.append(row)
    delta={key:rows[-1][key]-rows[0][key] for key in ['rss_bytes',*counters]}
    delta['elapsed_seconds']=rows[-1]['monotonic_seconds']-rows[0]['monotonic_seconds']
    return result('psutil.Process.memory_info / swap_memory / /proc/PID/stat',
                  dict(pid=pid,samples=rows,delta=delta),
                  units={'rss':'bytes','swap':'bytes','faults':'count','elapsed':'seconds'},limitations=[
                      '各字段顺序读取，不是原子快照；monotonic用于区间，UTC用于证据时间。',
                      'swap为系统累计计数，不等于该进程IO；RSS、minor/major faults与抖动不同。',
                      '采样间可能遗漏短暂变化；非Linux不提供/proc缺页计数。'])
