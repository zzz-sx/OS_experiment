"""学生算法实现区：页面置换、CPU调度与磁盘分配。"""
from lab_common import integer,StudentTaskPending
import random

REFERENCE=[7,0,1,2,0,3,0,4,2,3,0,3,2]
JOBS=[dict(id='A',arrival=0,burst=5),dict(id='B',arrival=1,burst=3),dict(id='C',arrival=2,burst=1)]
DISK_OPS=[('create','A',8),('create','B',5),('create','C',6),('delete','B',0),('create','D',7)]


def page_replace(pages,frames=3,algorithm='FIFO',seed=42) -> dict:
    """【A1】页面置换教学模拟，纯函数，不读真实内存、不改内核。

    基础FIFO/LRU/CLOCK/OPT；进阶RANDOM/SECOND_CHANCE/HYBRID按课程要求实现。
    若暂未实现某策略，必须继续抛StudentTaskPending，勿假借其他算法的结果。
    输入1..128页号(0..4095)，frames=1..16；bool不可作为整数；固定seed。
    输出至少：algorithm、selected_algorithm、seed、frame_count、faults、fault_rate、
    log、assumptions。log每步含step(从1)、page、hit、evicted(无则None)、frames。
    CLOCK/SECOND_CHANCE另保留reference_bits、hand、cleared_slots以支持推演。
    空闲页框先填充，命中不增加faults；fault_rate=缺页次数/引用长度。
    边界：单页框、全重复、淘汰页号0、同优先级、非法算法、局部随机源。
    OPT可预知未来，须说明假设；HYBRID启发式自行定义规则，不能宣称总更优。
    提示：先手算短序列并保存逐步状态，再写策略；不要只返回一个缺页总数。
    """
    integer(frames,1,16,'frames');integer(seed,0,2**32-1,'seed')
    if not isinstance(pages,list) or not 1<=len(pages)<=128:raise ValueError('pages: list of 1..128 integers')
    for page in pages:integer(page,0,4095,'page')
    if algorithm in ('SECOND_CHANCE','HYBRID'):
        raise StudentTaskPending('A1','students/algorithms.py:page_replace')
    if algorithm not in ('FIFO','LRU','CLOCK','OPT','RANDOM'):raise ValueError('unknown page replacement algorithm')
    state=[None]*frames;last_used=[-1]*frames;bits=[0]*frames
    hand=fifo_hand=faults=0;log=[];rng=random.Random(seed)
    for index,page in enumerate(pages):
        hit=page in state;evicted=None;cleared=[]
        if hit:slot=state.index(page)
        else:
            faults+=1
            if None in state:slot=state.index(None)
            elif algorithm=='FIFO':
                slot=fifo_hand;fifo_hand=(fifo_hand+1)%frames
            elif algorithm=='LRU':slot=min(range(frames),key=lambda n:last_used[n])
            elif algorithm=='OPT':
                def next_use(n):
                    return next((j for j in range(index+1,len(pages)) if pages[j]==state[n]),len(pages))
                slot=max(range(frames),key=next_use)
            elif algorithm=='RANDOM':slot=rng.randrange(frames)
            else:
                while bits[hand]:
                    bits[hand]=0;cleared.append(hand);hand=(hand+1)%frames
                slot=hand
            evicted=state[slot];state[slot]=page
            if algorithm=='CLOCK':hand=(slot+1)%frames
        last_used[slot]=index
        if algorithm=='CLOCK':bits[slot]=1
        row=dict(step=index+1,page=page,hit=hit,evicted=evicted,frames=state.copy())
        if algorithm=='CLOCK':row.update(reference_bits=bits.copy(),hand=hand,cleared_slots=cleared)
        log.append(row)
    assumptions=['空页框用null表示；空闲槽按下标填充；确定性策略并列候选选择最低槽号；时间为引用步数。']
    if algorithm=='OPT':assumptions.append('OPT预知全部未来引用，只作离线比较下界，不能在线实现。')
    if algorithm=='RANDOM':assumptions.append('局部Random(seed)仅在满框缺页时均匀选择槽，不改变全局随机状态；不保证优于其他策略。')
    return dict(algorithm=algorithm,selected_algorithm=algorithm,seed=seed,frame_count=frames,
                faults=faults,fault_rate=faults/len(pages),log=log,assumptions=assumptions)


def scheduler(jobs,algorithm='RR',quantum=2,boost_interval=20) -> dict:
    """【A2】单CPU离散tick调度：FCFS/SJF/RR基础，MLFQ进阶。

    jobs为1..12字典，每项id(唯一、1..12字符、禁用IDLE)、arrival(0..50)、
    burst或bursts二选一。bursts是奇数长度1..9的CPU/IO交替列表，每项1..30，
    每任务总量<=90。priority(0/1/2)为MLFQ初始级，默认0。
    SJF在已到达就绪任务中选下一段CPU最短，采用非抢占；不能先运行未来任务。
    RR边界先处理新到达/IO完成，再放回时间片用尽任务；保留稳定输入顺序。
    MLFQ进阶规则：q/2q/4q三级、耗尽配额降级、高优先级抢占、周期提升，
    boost_interval=0关闭提升；IO返回配额规则须明确，与自己的报告保持一致。
    输出algorithm、timeline([{id,start,end}])、jobs逐任务指标、events、
    mean_waiting、mean_response、mean_turnaround、cpu_utilization、assumptions。
    每任务含completion/turnaround/waiting/response/cpu_time/io_time/max_ready_wait。
    响应=首次运行-到达；周转=完成-到达；等待不含IO；周转=等待+CPU+IO。
    无就绪任务记录IDLE；固定模拟上限避免无限循环。只比较有限输入，不证明无饥饿。
    """
    integer(quantum,1,10,'quantum');integer(boost_interval,0,100,'boost_interval')
    if algorithm=='MLFQ':raise StudentTaskPending('A2','students/algorithms.py:scheduler')
    if algorithm not in ('FCFS','SJF','RR'):raise ValueError('unknown scheduling algorithm')
    if not isinstance(jobs,list) or not 1<=len(jobs)<=12:raise ValueError('jobs: list of 1..12 jobs')
    tasks={}
    for spec in jobs:
        name=spec.get('id')
        if not isinstance(name,str) or not 1<=len(name)<=12 or name=='IDLE' or name in tasks:
            raise ValueError('job id must be unique, 1..12 characters and not IDLE')
        arrival=integer(spec.get('arrival'),0,50,'arrival')
        if ('burst' in spec)==('bursts' in spec):raise ValueError('job requires exactly one of burst and bursts')
        bursts=spec['bursts'] if 'bursts' in spec else [spec['burst']]
        if not isinstance(bursts,list) or len(bursts) not in (1,3,5,7,9):
            raise ValueError('bursts must be 1..9 alternating CPU/IO ticks, ending in CPU')
        for value in bursts:integer(value,1,30,'burst')
        if sum(bursts)>90:raise ValueError('job total exceeds 90 ticks')
        tasks[name]=dict(arrival=arrival,bursts=bursts,position=0,left=bursts[0],wake=arrival,
                         first=None,completion=None,waiting=0,max_ready_wait=0)

    ready=[];timeline=[];events=[];running=expired=None;used=done=0
    end_bound=max(t['arrival'] for t in tasks.values())+sum(sum(t['bursts']) for t in tasks.values())
    for tick in range(end_bound):
        # 同一tick按输入顺序处理到达与IO完成，之后才让用完时间片的任务回队。
        for name,task in tasks.items():
            if task['wake']==tick:
                ready.append(name);task['ready_since']=tick;task['wake']=None
                events.append(dict(tick=tick,id=name,event='arrival' if task['position']==0 else 'io_complete'))
        if expired is not None:
            ready.append(expired);tasks[expired]['ready_since']=tick;expired=None
        if running is None and ready:
            next_index=min(range(len(ready)),key=lambda i:tasks[ready[i]]['left']) if algorithm=='SJF' else 0
            running=ready.pop(next_index);task=tasks[running];used=0
            waited=tick-task['ready_since'];task['waiting']+=waited
            task['max_ready_wait']=max(task['max_ready_wait'],waited)
            if task['first'] is None:task['first']=tick
        active=running if running is not None else 'IDLE'
        if timeline and timeline[-1]['id']==active:timeline[-1]['end']=tick+1
        else:timeline.append(dict(id=active,start=tick,end=tick+1))
        if running is None:continue
        task=tasks[running];task['left']-=1;used+=1
        if task['left']==0:
            pos=task['position'];bursts=task['bursts']
            if pos+1==len(bursts):
                task['completion']=tick+1;done+=1
                events.append(dict(tick=tick+1,id=running,event='complete'))
            else:
                task['wake']=tick+1+bursts[pos+1];task['position']=pos+2;task['left']=bursts[pos+2]
                events.append(dict(tick=tick+1,id=running,event='io_start',until=task['wake']))
            running=None
        elif algorithm=='RR' and used==quantum:
            events.append(dict(tick=tick+1,id=running,event='quantum_expired'))
            expired=running;running=None
        if done==len(tasks):break

    rows=[dict(id=name,completion=t['completion'],turnaround=t['completion']-t['arrival'],
               waiting=t['waiting'],response=t['first']-t['arrival'],cpu_time=sum(t['bursts'][::2]),
               io_time=sum(t['bursts'][1::2]),max_ready_wait=t['max_ready_wait']) for name,t in tasks.items()]
    return dict(algorithm=algorithm,timeline=timeline,jobs=rows,events=events,
                mean_waiting=sum(r['waiting'] for r in rows)/len(rows),
                mean_response=sum(r['response'] for r in rows)/len(rows),
                mean_turnaround=sum(r['turnaround'] for r in rows)/len(rows),
                cpu_utilization=sum(r['cpu_time'] for r in rows)/timeline[-1]['end'],
                assumptions=['单CPU，IO独立等待且可重叠，切换无额外耗时；利用率为0..1。',
                             'FCFS/SJF不抢占；SJF比较已就绪任务的下一CPU段，并列按就绪顺序。',
                             'RR先接收到达及IO完成任务，再把用完时间片的任务放回队尾。'])


def disk_allocate(strategy='contiguous',blocks=24,operations=None,block_size=4096) -> dict:
    """【A3】抽象磁盘块的连续/链接/单级索引分配，不改真实磁盘。

    operations=None采用DISK_OPS。每项action=create/delete、name；create的blocks与
    size_bytes二选一。blocks表示请求的数据块数量；size_bytes表示准确逻辑字节。
    允许1..128块、1..32操作、block_size=64..65536。链接指针8字节，索引块一块，
    单索引容量为block_size//8。分别记录逻辑字节、元数据和尾块浪费。
    创建失败不得留下部分分配；删除不存在/重复创建需记录错误；块号0有效。
    输出strategy、block_count、block_size_bytes、files、log、assumptions。
    每步log含operation、success、error、map、allocated_this_step、index_block、
    free_blocks、largest_free_run、free_run_fragmentation、logical_bytes、
    internal_waste_bytes、metadata_bytes、allocated_fraction。
    free_run_fragmentation按1-最大空闲连续段/总空闲定义，无空闲时为0，
    必须说明它是模拟指标。选做toy_head_path/distance不能标为SSD延迟。
    提示：先设计空闲块表示和事务式分配，画出同操作序列下三种策略的块图。
    """
    integer(blocks,1,128,'blocks');integer(block_size,64,65536,'block_size')
    if strategy not in ('contiguous','linked','indexed'):raise ValueError('unknown disk allocation strategy')
    if operations is None:
        operations=[dict(action=action,name=name,**({'blocks':count} if action=='create' else {}))
                    for action,name,count in DISK_OPS]
    if not isinstance(operations,list) or not 1<=len(operations)<=32:
        raise ValueError('operations: list of 1..32 operations')
    state=[None]*blocks;files={};log=[]
    payload=block_size-8 if strategy=='linked' else block_size

    def free_runs():
        start=0
        for end,owner in enumerate([*state,'end']):
            if owner is not None:
                if end>start:yield start,end-start
                start=end+1

    for op in operations:
        action=op.get('action');name=op.get('name')
        if action not in ('create','delete') or not isinstance(name,str) or not name:
            raise ValueError('operation requires action create/delete and a nonempty name')
        selected=[];index_block=None;error=None
        if action=='delete':
            if name not in files:error='FILE_NOT_FOUND'
            else:
                record=files.pop(name)
                for slot in record['blocks']:state[slot]=None
                if record['index_block'] is not None:state[record['index_block']]=None
        else:
            if ('blocks' in op)==('size_bytes' in op):raise ValueError('create requires exactly one of blocks and size_bytes')
            if 'blocks' in op:
                needed=integer(op['blocks'],1,128,'operation blocks')
                logical=needed*payload
            else:
                logical=op['size_bytes']
                if type(logical) is not int or logical<=0:raise ValueError('size_bytes must be a positive integer')
                needed=(logical+payload-1)//payload
            free=[i for i,owner in enumerate(state) if owner is None]
            if name in files:error='FILE_EXISTS'
            elif strategy=='indexed' and needed>block_size//8:error='INDEX_CAPACITY_EXCEEDED'
            elif len(free)<needed+(strategy=='indexed'):error='INSUFFICIENT_FREE_BLOCKS'
            elif strategy=='contiguous':
                start=next((start for start,length in free_runs() if length>=needed),None)
                if start is None:error='NO_CONTIGUOUS_RUN'
                else:selected=list(range(start,start+needed))
            elif strategy=='linked':selected=free[:needed]
            else:index_block=free[0];selected=free[1:needed+1]
            if error is None:
                for slot in selected:state[slot]=name
                if index_block is not None:state[index_block]=name
                metadata=needed*8 if strategy=='linked' else block_size if strategy=='indexed' else 0
                files[name]=dict(blocks=selected,index_block=index_block,logical_bytes=logical,
                                 internal_waste_bytes=needed*payload-logical,metadata_bytes=metadata)
        free_count=state.count(None)
        largest=max((length for _,length in free_runs()),default=0)
        log.append(dict(operation=op,success=error is None,error=error,map=state.copy(),
                        allocated_this_step=selected,index_block=index_block,free_blocks=free_count,
                        largest_free_run=largest,free_run_fragmentation=1-largest/free_count if free_count else 0,
                        logical_bytes=sum(f['logical_bytes'] for f in files.values()),
                        internal_waste_bytes=sum(f['internal_waste_bytes'] for f in files.values()),
                        metadata_bytes=sum(f['metadata_bytes'] for f in files.values()),
                        allocated_fraction=(blocks-free_count)/blocks))
    return dict(strategy=strategy,block_count=blocks,block_size_bytes=block_size,files=files,log=log,
                assumptions=['按块号从小到大分配；连续分配选首个足够长的空闲段。',
                             '链接每数据块内置8字节指针；索引用独立索引块，allocated_this_step仅列数据块。',
                             'blocks指定数据块数量，逻辑字节按该策略数据块满载计算；size_bytes指定准确字节。',
                             '每步字节指标按当时所有文件汇总；空闲段碎片率为教学模拟指标。'])
