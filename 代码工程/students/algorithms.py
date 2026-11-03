"""学生算法实现区：只提供契约、输入样例和约束，不含完整算法答案。"""
from lab_common import integer,StudentTaskPending

REFERENCE=[7,0,1,2,0,3,0,4,2,3,0,3,2]
JOBS=[dict(id='A',arrival=0,burst=5),dict(id='B',arrival=1,burst=3),dict(id='C',arrival=2,burst=1)]
DISK_OPS=[('create','A',8),('create','B',5),('create','C',6),('delete','B',0),('create','D',7)]


def page_replace(pages,frames=3,algorithm='FIFO',seed=42) -> dict:
    """【TODO A1】页面置换教学模拟，纯函数，不读真实内存、不改内核。

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
    # TODO：输入校验、策略状态与每次引用的轨迹。可分阶段完成各算法。
    raise StudentTaskPending('A1','students/algorithms.py:page_replace')


def scheduler(jobs,algorithm='RR',quantum=2,boost_interval=20) -> dict:
    """【TODO A2】单CPU离散tick调度：FCFS/SJF/RR基础，MLFQ进阶。

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
    # TODO：校验输入，维护pending/ready/running/blocked/done，生成轨迹和指标。
    raise StudentTaskPending('A2','students/algorithms.py:scheduler')


def disk_allocate(strategy='contiguous',blocks=24,operations=None,block_size=4096) -> dict:
    """【TODO A3】抽象磁盘块的连续/链接/单级索引分配，不改真实磁盘。

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
    # TODO：分配、释放、失败回滚、空间成本与逐步块图。
    raise StudentTaskPending('A3','students/algorithms.py:disk_allocate')
