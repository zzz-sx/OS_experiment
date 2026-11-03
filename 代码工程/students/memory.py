"""内存实验。get_memory_info是已提供的示例，其余TODO由学生完成。"""
from lab_common import psutil,result,own_process,integer,duration,StudentTaskPending
from students.algorithms import REFERENCE,page_replace


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
    """【TODO M1】列出同用户进程中RSS最高的limit项。

    输入：limit为1..10，基本参数校验已提供。
    输出：result(...,data={'processes':[{'pid':int,'ppid':int,'name':str,
        'rss':int}], 'excluded':int},units={'rss':'bytes'})，kind=observation。
    行为：只统计当前真实UID；RSS降序；少于limit时返回全部实际项。
    边界：遍历时进程可退出或拒绝访问，跳过并记录excluded；不能伪造PID。
    提示：查看psutil.process_iter，避免向模型发送命令行或环境中的秘密。
    """
    integer(limit,1,10,'limit')
    # TODO：过滤、采样和排序；每项结果必须来自当前真实进程。
    raise StudentTaskPending('M1','students/memory.py:list_top_processes')


def parse_smaps(text: str,limit: int=12) -> list:
    """【TODO M2a】将给定的Linux smaps文本解析为最多limit个映射。

    返回list[dict]，每项含address、permissions、label及实际存在的
    Size_KiB、Rss_KiB、Pss_KiB、Private_Dirty_KiB。值按KiB保留，缺字段不补0。
    处理多映射、匿名段、空输入、不含PSS的记录及最后一段。
    label仅保留文件基名或[heap]一类标签，不泄露完整文件路径。
    这是纯解析函数，可在任意平台用人工短文本独立测试。
    """
    integer(limit,1,20,'limit')
    # TODO：识别映射头与后续指标的所属关系，截断需由调用者声明。
    raise StudentTaskPending('M2a','students/memory.py:parse_smaps')


def get_process_memory(pid: int,max_maps: int=12) -> dict:
    """【TODO M2】读取同用户进程RSS与有界smaps映射。

    own_process权限检查已提供。输出data含pid、name、memory(psutil字节字段)、
    maps(parse_smaps结果)、maps_partial。读取文本最多2,000,000字节，映射最多20。
    Linux读/proc/PID/smaps；其他平台可保留psutil项并声明maps不可用。
    RSS可能重复计入共享页，不能等同私有物理内存；一次映射列表可不完整。
    若进程退出/权限拒绝，让异常交给Server返回错误，勿返回成功的零值。
    """
    integer(max_maps,1,20,'max_maps');proc=own_process(pid)
    # TODO：真实读取proc、调用自己的parse_smaps，再使用result封装。
    raise StudentTaskPending('M2','students/memory.py:get_process_memory')


def analyze_memory_patterns(pages: list[int]|None=None) -> dict:
    """【TODO M3】分析显式引用序列的复用与相邻页号代理指标。

    None使用REFERENCE。1..128项，每项0..4095的整数，禁止bool。
    输出data：length、distinct_pages、repeated_references、mean_reuse_interval、
    adjacent_page_ratio。复用间隔定义为同页相邻两次出现的索引之差；无复用为None。
    相邻比例定义为相邻访问中abs(页号差)<=1的比例；单项序列定义为0。
    kind=simulation；单位分别为references与fraction。
    结果仅描述输入序列，不能由此认定当前真实程序的时间/空间局部性。
    """
    pages=REFERENCE if pages is None else pages
    # TODO：校验序列、定义分母和无复用情况，再计算指标。
    raise StudentTaskPending('M3','students/memory.py:analyze_memory_patterns')


def simulate_page_fault(algorithm='FIFO',frames=3,pages=None,seed=42) -> dict:
    """【已提供调用框架】计算逻辑位于students/algorithms.py的A1。

    完成page_replace后本接口即可调用；未实现异常由Server变成NOT_IMPLEMENTED。
    """
    return result('students.algorithms.page_replace',
                  page_replace(REFERENCE if pages is None else pages,frames,algorithm,seed),
                  kind='simulation',units={'fault_rate':'fraction','faults':'count'})


def read_proc_faults(pid: int) -> dict:
    """【TODO M4a】解析/proc/PID/stat中的minor_faults、major_faults累计计数。

    输出{'minor_faults':int,'major_faults':int}。comm名称可含空格及括号，不能对
    整行直接split后用固定下标。调用者负责同用户检查；本函数不改内核计数。
    可自行另写纯文本解析函数，用包含特殊comm的短样本验证字段位置。
    """
    raise StudentTaskPending('M4a','students/memory.py:read_proc_faults')


def sample_process_memory(pid: int,samples=3,interval=0.2) -> dict:
    """【TODO M4】对同用户存活进程做有界时间序列采样。

    samples=2..10、interval=0.1..0.5秒。保留创建时间以识别PID复用。
    data含pid、samples(list)、delta(dict)。每行有sampled_at、monotonic_seconds、
    rss_bytes、system_swap_in_bytes、system_swap_out_bytes，Linux加minor/major_faults。
    delta为末项减首项；两种时钟用途不同，实际间隔需保留。不可无限采样。
    全局swap差不等于该进程IO；minor/major fault、RSS变化和抖动须区分。
    """
    integer(samples,2,10,'samples');duration(interval,0.1,0.5);proc=own_process(pid)
    # TODO：采样、存活和PID复用检查、计数差与局限说明。
    raise StudentTaskPending('M4','students/memory.py:sample_process_memory')
