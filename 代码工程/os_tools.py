"""已提供的统一门面。Server通过本文件调用学生模块，保留原接口名称。"""
from lab_common import psutil,result,ROOT,safe_path,own_process,StudentTaskPending
from students.memory import (get_memory_info,list_top_processes,parse_smaps,
    get_process_memory,analyze_memory_patterns,simulate_page_fault,
    read_proc_faults,sample_process_memory)
from students.filesystem import (get_filesystem_info,analyze_file_distribution,
    trace_file_access,simulate_disk_allocation)
from students.process import (get_process_tree,monitor_context_switches,
    parse_cpu,analyze_scheduling,simulate_scheduler,get_process_schedstat)


def get_time() -> dict:
    """已提供：UTC基础通信。时间由统一结果中的sampled_at字段给出。"""
    return result('Python datetime',{'timezone':'UTC'},kind='status')
