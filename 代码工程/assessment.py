"""已提供：结果契约与不变量检查，不含操作系统实现。"""
REQUIRED={'ok','kind','sampled_at','platform','source','units','data','error','limitations'}


def check_result(tool,value):
    if not isinstance(value,dict) or not REQUIRED<=value.keys():raise AssertionError('缺统一结果字段')
    if not isinstance(value['ok'],bool):raise AssertionError('ok必须是bool')
    if not value['ok']:
        if not value['error']:raise AssertionError('失败必须有error')
        return
    if value['error'] is not None:raise AssertionError('成功结果error应为None')
    if not value['sampled_at'] or not value['source']:raise AssertionError('缺时间或来源')
    data=value['data']
    if not isinstance(data,dict):raise AssertionError('data必须是dict')
    if tool=='get_memory_info':assert 0<=data['available']<=data['total'] and data['total']>0
    elif tool=='list_top_processes':
        rows=data['processes'];assert all(r['pid']>0 and r['rss']>=0 for r in rows)
        assert [r['rss'] for r in rows]==sorted((r['rss'] for r in rows),reverse=True)
    elif tool=='get_process_memory':assert data['pid']>0 and data['memory']['rss']>=0 and isinstance(data['maps'],list)
    elif tool=='sample_process_memory':assert len(data['samples'])>=2 and isinstance(data['delta'],dict)
    elif tool=='analyze_memory_patterns':
        assert data['length']>0 and 0<=data['adjacent_page_ratio']<=1
        assert data['distinct_pages']+data['repeated_references']==data['length']
    elif tool=='simulate_page_fault':
        assert value['kind']=='simulation' and len(data['log'])>0
        assert data['faults']==sum(not s['hit'] for s in data['log'])
        assert abs(data['fault_rate']-data['faults']/len(data['log']))<1e-8
    elif tool=='get_filesystem_info':
        assert data['capacity']['total']>0 and data['capacity']['free']>=0
        assert data['inodes_used']==data['inodes_total']-data['inodes_free']
    elif tool=='analyze_file_distribution':
        assert isinstance(data['partial'],bool) and data['skipped']>=0
        assert all(n>=0 for n in data['count_by_extension'].values())
    elif tool=='trace_file_access':
        assert isinstance(data['events'],list) and len(data['events'])<=32
        assert 0<=data['duration_seconds']<=data['requested_seconds']+2
    elif tool=='simulate_disk_allocation':
        assert value['kind']=='simulation' and data['log']
        for step in data['log']:
            assert len(step['map'])==data['block_count']
            assert step['free_blocks']==sum(x is None for x in step['map'])
            assert 0<=step['largest_free_run']<=step['free_blocks']
    elif tool=='get_process_tree':assert len({n['pid'] for n in data['nodes']})==len(data['nodes'])
    elif tool=='monitor_context_switches':
        assert data['elapsed_seconds']>0
        if isinstance(data['delta'],dict):
            assert all(v>=0 for v in data['delta'].values())
            for k,v in data['delta'].items():assert abs(data['rate_per_second'][k]-v/data['elapsed_seconds'])<1e-5
        else:assert data['delta']>=0 and abs(data['rate_per_second']-data['delta']/data['elapsed_seconds'])<1e-5
    elif tool=='analyze_scheduling':
        assert data['total_ticks']>0 and len(data['raw_delta_ticks'])==8
        assert abs(sum(v for k,v in data.items() if k.endswith('_percent'))-100)<1e-5
    elif tool=='get_process_schedstat':
        if str(data['schedstats_enabled'])!='1' or data['timeslices']==0:assert data['mean_runqueue_wait_ns'] is None
    elif tool=='simulate_scheduler':
        assert value['kind']=='simulation' and data['jobs'] and data['timeline']
        for job in data['jobs']:
            assert job['turnaround']==job['waiting']+job['cpu_time']+job['io_time']
            assert job['response']>=0 and job['waiting']>=0


def stage_status(records):
    if any(r['status']=='FAILED' for r in records):return 'failed'
    if any(r['status']=='NOT_IMPLEMENTED' for r in records):return 'not_implemented'
    if any(r['status']=='UNSUPPORTED_PLATFORM' for r in records):return 'unsupported_platform'
    return 'passed'
