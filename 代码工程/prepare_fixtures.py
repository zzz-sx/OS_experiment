"""已提供：固定小样本，与学生待实现的文件统计分离。"""
from pathlib import Path
BASE=Path(__file__).resolve().parent


def prepare():
    root=BASE/'lab-data';root.mkdir(exist_ok=True,mode=0o700)
    if root.is_symlink():raise ValueError('lab-data不能是符号链接')
    for name,size in [('notes.txt',4096),('sample.csv',8192),('cache.bin',65536)]:
        path=root/name
        if path.is_symlink():raise ValueError('固定样本不能为符号链接')
        if not path.exists():
            with path.open('xb') as f:f.write(b'x'*size)
    return root


if __name__=='__main__':print(prepare())
