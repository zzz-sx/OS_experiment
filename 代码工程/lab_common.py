"""已提供：结果信封、任务状态、输入约束和权限边界。学生实现复用本文件。"""
import os,platform
from datetime import datetime,timezone
from pathlib import Path
import psutil
BASE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('OSLAB_ROOT',str(BASE/'lab-data'))).resolve()

class StudentTaskPending(NotImplementedError):
    def __init__(self,task,location):
        self.task,self.location=task,location
        super().__init__(f'TODO {task}：请完成 {location}，当前未执行该功能。')

def integer(value,low,high,name):
    if type(value) is not int or not low<=value<=high:
        raise ValueError(f'{name}: integer {low}..{high}')
    return value

def result(source, data=None, kind='observation', units=None, error=None, limitations=None):
    return dict(ok=error is None, kind=kind,
                sampled_at=datetime.now(timezone.utc).isoformat(),
                platform=platform.system(), source=source, units=units or {},
                data=data, error=error, limitations=limitations or [])

def safe_path(value='.'):
    if not isinstance(value,str) or len(value)>200:
        raise ValueError('path: string <=200 chars')
    raw = ROOT/value
    if any(p.is_symlink() for p in [raw,*raw.parents] if p!=ROOT and p.is_relative_to(ROOT)):
        raise ValueError('symlink paths are not allowed')
    path = raw.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('path must stay inside OSLAB_ROOT')
    if not path.exists():
        raise ValueError('path does not exist; run prepare_lab.py first')
    return path

def own_process(pid):
    integer(pid,1,2147483647,'pid')
    proc = psutil.Process(pid)
    if not hasattr(os, 'getuid') or proc.uids().real != os.getuid():
        raise ValueError('only processes owned by the current user are allowed')
    return proc

def duration(value, low, high):
    import math
    if type(value) not in (float,int) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'duration must be {low}..{high} seconds')
