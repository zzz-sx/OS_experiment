"""stdio-only MCP Server. 日志交由 SDK 写 stderr，stdout 专供 MCP。"""
import functools
import os
from typing import Annotated, Literal
from pydantic import Field
from mcp.server.fastmcp import FastMCP
import os_tools as ops
from lab_common import StudentTaskPending

mcp = FastMCP('openEuler OS laboratory')


def bounded(fn):
    @functools.wraps(fn)
    def wrap(*args,**kwargs):
        try:
            return fn(*args,**kwargs)
        except StudentTaskPending as exc:
            value=ops.result(fn.__name__,kind='status',error='NOT_IMPLEMENTED')
            value.update(task=exc.task,location=exc.location,message=str(exc))
            return value
        except (ValueError, OSError, ops.psutil.Error, NotImplementedError) as exc:
            return ops.result(fn.__name__,error=f'{type(exc).__name__}: {str(exc)[:240]}')
    return wrap


@mcp.tool()
@bounded
def get_time() -> dict:
    """返回 Server 的 UTC 时间，验证 MCP 通信。"""
    return ops.get_time()

@mcp.tool()
@bounded
def get_memory_info() -> dict:
    """采集当前系统内存和交换区计数；一次快照不能证明抖动。"""
    return ops.get_memory_info()

@mcp.tool()
@bounded
def list_top_processes(limit: Annotated[int,Field(ge=1,le=10)]=5) -> dict:
    """列出当前用户可见进程中 RSS 最高的进程，最多十个。"""
    return ops.list_top_processes(limit)

@mcp.tool()
@bounded
def get_process_memory(pid: Annotated[int,Field(ge=1)],max_maps: Annotated[int,Field(ge=1,le=20)]=12) -> dict:
    """采集指定同用户进程的内存和部分映射；PID 必须先从工具结果获得。"""
    return ops.get_process_memory(pid,max_maps)

@mcp.tool()
@bounded
def analyze_memory_patterns(pages: Annotated[list[int],Field(min_length=1,max_length=128)]|None=None) -> dict:
    """只分析显式页面引用序列的重复间隔与相邻比例；不代表真实系统访问模式。"""
    return ops.analyze_memory_patterns(pages)

@mcp.tool()
@bounded
def simulate_page_fault(algorithm: Literal['FIFO','LRU','CLOCK','OPT','RANDOM','SECOND_CHANCE','HYBRID']='FIFO',frames: Annotated[int,Field(ge=1,le=16)]=3,pages: Annotated[list[int],Field(min_length=1,max_length=128)]|None=None,seed: Annotated[int,Field(ge=0,le=4294967295)]=42) -> dict:
    """教学模拟页面置换，返回缺页率和逐步日志；不改变内核。"""
    return ops.simulate_page_fault(algorithm,frames,pages,seed)

@mcp.tool()
@bounded
def get_filesystem_info(path: Annotated[str,Field(max_length=200)]='.') -> dict:
    """查询实验目录所在文件系统的容量与 inode 数，不测碎片率。"""
    return ops.get_filesystem_info(path)

@mcp.tool()
@bounded
def analyze_file_distribution(path: Annotated[str,Field(max_length=200)]='.',max_files: Annotated[int,Field(ge=1,le=500)]=500) -> dict:
    """在实验目录内按扩展名和修改时间统计文件；拒绝越界路径，不跟随符号链接。"""
    return ops.analyze_file_distribution(path,max_files)

@mcp.tool()
@bounded
def trace_file_access(path: Annotated[str,Field(max_length=200)]='.',seconds: Annotated[float,Field(ge=0.1,le=10)]=3) -> dict:
    """Linux inotify 限时观察单层路径的事件，不能统计每次 read 或读取字节数。"""
    return ops.trace_file_access(path,seconds)

@mcp.tool()
@bounded
def simulate_disk_allocation(strategy: Literal['contiguous','linked','indexed']='contiguous',blocks: Annotated[int,Field(ge=1,le=128)]=24,operations: Annotated[list[dict],Field(min_length=1,max_length=32)]|None=None,block_size: Annotated[int,Field(ge=64,le=65536)]=4096) -> dict:
    """离散磁盘块分配模拟，返回分配图；不向真实磁盘写入模拟文件。"""
    return ops.simulate_disk_allocation(strategy,blocks,operations,block_size)

@mcp.tool()
@bounded
def get_process_tree(limit: Annotated[int,Field(ge=1,le=100)]=50) -> dict:
    """返回当前用户可见进程的 PID、PPID、名称，父节点可能在范围外。"""
    return ops.get_process_tree(limit)

@mcp.tool()
@bounded
def monitor_context_switches(pid: Annotated[int,Field(ge=1)]|None=None,seconds: Annotated[float,Field(ge=0.1,le=5)]=1) -> dict:
    """pid省略时采样系统计数差，指定时采样同用户进程的自愿与非自愿切换差，不推断每次切换开销。"""
    return ops.monitor_context_switches(pid,seconds)

@mcp.tool()
@bounded
def simulate_scheduler(algorithm: Literal['FCFS','SJF','RR','MLFQ']='RR',quantum: Annotated[int,Field(ge=1,le=10)]=2,jobs: Annotated[list[dict],Field(min_length=1,max_length=12)]|None=None,boost_interval: Annotated[int,Field(ge=0,le=100)]=20) -> dict:
    """单CPU教学调度，任务为id/arrival/burst或交替CPU与IO的bursts；支持MLFQ提升与抢占。"""
    return ops.simulate_scheduler(algorithm,quantum,jobs,boost_interval)

@mcp.tool()
@bounded
def analyze_scheduling(seconds: Annotated[float,Field(ge=0.1,le=5)]=1) -> dict:
    """Linux 两次 /proc/stat 采样的 CPU 时间比例，不能直接测调度延迟。"""
    return ops.analyze_scheduling(seconds)


@mcp.tool()
@bounded
def sample_process_memory(pid: Annotated[int,Field(ge=1)],samples: Annotated[int,Field(ge=2,le=10)]=3,interval: Annotated[float,Field(ge=0.1,le=0.5)]=0.2) -> dict:
    """限时重复采样同用户进程RSS、minor/major faults与全局swap差，不把它们混为抖动。"""
    return ops.sample_process_memory(pid,samples,interval)

@mcp.tool()
@bounded
def get_process_schedstat(pid: Annotated[int,Field(ge=1)],seconds: Annotated[float,Field(ge=0.1,le=5)]=0.2) -> dict:
    """读取同用户进程的schedstat区间差；未启用调度统计时明确降级，不更改内核设置。"""
    return ops.get_process_schedstat(pid,seconds)

GROUPS = {
 'memory': {'get_time','get_memory_info','list_top_processes','get_process_memory','analyze_memory_patterns','simulate_page_fault','sample_process_memory'},
 'filesystem': {'get_time','get_filesystem_info','analyze_file_distribution','trace_file_access','simulate_disk_allocation'},
 'process': {'get_time','get_process_tree','monitor_context_switches','simulate_scheduler','analyze_scheduling','get_process_schedstat'},
}


def main():
    import argparse, asyncio
    parser=argparse.ArgumentParser()
    parser.add_argument('--module',choices=['all',*GROUPS],default='all')
    args=parser.parse_args()
    if hasattr(os,'geteuid') and os.geteuid()==0:
        raise SystemExit('请用普通实验用户运行 MCP Server，不使用 root。')
    if args.module!='all':
        for tool in asyncio.run(mcp.list_tools()):
            if tool.name not in GROUPS[args.module]: mcp.remove_tool(tool.name)
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
