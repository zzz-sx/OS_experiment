"""文件系统实验。目录限制和协议封装已提供，采集/事件由学生实现。"""
import ctypes,os,platform,select,stat,struct,time
from pathlib import Path
from lab_common import ROOT,safe_path,result,integer,duration,psutil
from students.algorithms import disk_allocate


def get_filesystem_info(path='.') -> dict:
    """【F1】查询实验目录所在文件系统容量和inode。

    path仅在lab-data内，safe_path已拒绝越界和符号链接。
    data含path(相对允许根目录)、capacity(total/used/free/percent)、
    inodes_total、inodes_free、inodes_used、inodes_available。容量单位bytes。
    区分f_ffree与f_favail；不支持inode时明确报不可用，不能补假值。
    容量属于所在文件系统，并非这个目录的大小；本接口不测碎片率。
    提示：阅读os.statvfs与psutil.disk_usage的字段语义。
    """
    target=safe_path(path)
    if not hasattr(os,'statvfs'):
        return result('os.statvfs',error='UNSUPPORTED_PLATFORM')
    inode=os.statvfs(target)
    if not inode.f_files:
        return result('os.statvfs',error='INODES_UNAVAILABLE')
    return result('psutil.disk_usage / os.statvfs',dict(
        path=target.relative_to(ROOT).as_posix(),capacity=psutil.disk_usage(target)._asdict(),
        inodes_total=inode.f_files,inodes_free=inode.f_ffree,inodes_used=inode.f_files-inode.f_ffree,
        inodes_available=inode.f_favail),units={'capacity':'bytes','percent':'percent','inodes':'count'},
        limitations=['容量属于路径所在文件系统，不是目录大小；free是普通用户可用空间，不测碎片率。'])


def analyze_file_distribution(path='.',max_files=500) -> dict:
    """【F2】在受限目录内统计文件分布，最多500条/3层/2秒。

    data含count_by_extension、logical_bytes_by_extension、allocated_bytes_by_extension、
    size_bucket_counts、modification_age_counts、largest_files(最多5项)、
    entries_scanned、skipped、partial。空目录应正常返回空统计。
    普通文件才进入文件计数；符号链接不跟随；拒绝越界。大小桶为<1KiB、
    1KiB..<1MiB、>=1MiB；时间桶0..1d、1..7d、7d+，说明未来mtime处理策略。
    用lstat区分逻辑大小和实际块分配字节；到达时间/深度/条数上限标partial。
    单项权限拒绝或文件并发删除须记录跳过，不使已采集内容冒充完整。
    """
    integer(max_files,1,500,'max_files');target=safe_path(path)
    if not target.is_dir():raise ValueError('directory required')
    if platform.system()!='Linux':
        return result('os.scandir / lstat',error='UNSUPPORTED_PLATFORM')
    deadline=time.monotonic()+2;now=time.time()
    data=dict(count_by_extension={},logical_bytes_by_extension={},allocated_bytes_by_extension={},
              size_bucket_counts={'<1KiB':0,'1KiB..<1MiB':0,'>=1MiB':0},
              modification_age_counts={'0..<1d':0,'1..<7d':0,'>=7d':0},largest_files=[],
              entries_scanned=0,skipped=0,partial=False)
    files=[]

    def scan(folder,level):
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if data['entries_scanned']>=max_files or time.monotonic()>=deadline:
                        data['partial']=True
                        return
                    data['entries_scanned']+=1
                    try:
                        info=entry.stat(follow_symlinks=False)
                    except (FileNotFoundError,PermissionError):
                        data['skipped']+=1;data['partial']=True
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        if level<3:scan(entry.path,level+1)
                        else:data['partial']=True
                    elif stat.S_ISREG(info.st_mode):
                        size=info.st_size;allocated=info.st_blocks*512
                        ext=Path(entry.name).suffix.lower() or '(none)'
                        for key,value in [('count_by_extension',1),('logical_bytes_by_extension',size),
                                          ('allocated_bytes_by_extension',allocated)]:
                            totals=data[key];totals[ext]=totals.get(ext,0)+value
                        data['size_bucket_counts']['<1KiB' if size<1024 else '1KiB..<1MiB' if size<1048576 else '>=1MiB']+=1
                        age=max(0,now-info.st_mtime)
                        data['modification_age_counts']['0..<1d' if age<86400 else '1..<7d' if age<604800 else '>=7d']+=1
                        files.append(dict(path=Path(entry.path).relative_to(ROOT).as_posix(),
                                          logical_bytes=size,allocated_bytes=allocated))
                    else:data['skipped']+=1
        except (FileNotFoundError,PermissionError):
            data['skipped']+=1;data['partial']=True

    scan(target,1)
    data['largest_files']=sorted(files,key=lambda f:(-f['logical_bytes'],f['path']))[:5]
    return result('os.scandir / lstat',data,units={'size':'bytes','age':'days','entries':'count'},
                  limitations=['只统计普通文件；不跟随符号链接。未来修改时间按0天计。',
                               '分配字节按st_blocks×512估计，不能推出碎片率。'])


def trace_file_access(path='.',seconds=3) -> dict:
    """【F3】Linux inotify有界观察单层目录事件。

    seconds=0.1..10；最多32事件；必须关闭文件描述符并按时返回。
    data含events([{name,events:[类型]}])、requested_seconds、duration_seconds、
    truncated、overflow。至少区分ACCESS/OPEN/MODIFY/CLOSE/CREATE/DELETE及溢出。
    平台不支持返回ok=false/error=UNSUPPORTED_PLATFORM；这不等于已实现。
    事件可能合并；不递归，不识别每次read的PID与字节数；空事件也不能证明无访问。
    提示：先查inotify系统接口；可以用ctypes或经课程确认的依赖，不必为事件提权。
    """
    duration(seconds,0.1,10);target=safe_path(path)
    if platform.system()!='Linux':
        return result('inotify',error='UNSUPPORTED_PLATFORM')
    masks={0x01:'ACCESS',0x02:'MODIFY',0x08:'CLOSE_WRITE',0x10:'CLOSE_NOWRITE',
           0x20:'OPEN',0x40:'MOVED_FROM',0x80:'MOVED_TO',0x100:'CREATE',0x200:'DELETE'}
    header=struct.Struct('iIII')
    libc=ctypes.CDLL(None,use_errno=True)
    fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
    if fd<0:raise OSError(ctypes.get_errno(),'inotify_init1')
    try:
        # IN_ONLYDIR | IN_DONT_FOLLOW，事件名称仅来自当前目录。
        if libc.inotify_add_watch(fd,os.fsencode(target),sum(masks)|0x03000000)<0:
            raise OSError(ctypes.get_errno(),'inotify_add_watch')
        events=[];overflow=False;started=time.monotonic()
        while len(events)<32:
            remaining=seconds-(time.monotonic()-started)
            if remaining<=0 or not select.select([fd],[],[],remaining)[0]:break
            batch=os.read(fd,4096);offset=0
            while offset<len(batch):
                _,mask,_,length=header.unpack_from(batch,offset);offset+=header.size
                name=batch[offset:offset+length].split(b'\0',1)[0].decode(errors='replace');offset+=length
                if mask&0x4000:overflow=True  # IN_Q_OVERFLOW
                labels=[label for bit,label in masks.items() if mask&bit]
                if labels and len(events)<32:events.append(dict(name=name,events=labels))
        elapsed=time.monotonic()-started
    finally:os.close(fd)
    return result('inotify',dict(events=events,requested_seconds=seconds,duration_seconds=elapsed,
                                 truncated=len(events)==32,overflow=overflow),units={'duration':'seconds'},
                  limitations=['事件可能合并，只观察一层，无法给出每次读取的PID或字节数；空列表不证明无访问。'])


def simulate_disk_allocation(strategy='contiguous',blocks=24,operations=None,block_size=4096) -> dict:
    """【已提供调用框架】学生实现A3后，本工具自动得到教学分配结果。"""
    return result('students.algorithms.disk_allocate',disk_allocate(strategy,blocks,operations,block_size),
                  kind='simulation',units={'space':'abstract blocks'})
