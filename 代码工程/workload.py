"""教师/学生手动启动的限时负载，不暴露为模型工具。"""
import argparse
import os
import time

p=argparse.ArgumentParser()
p.add_argument('--mode',choices=['memory','cpu','sleep'],default='memory')
p.add_argument('--mib',type=int,default=32)
p.add_argument('--seconds',type=int,default=15)
a=p.parse_args()
if not 1<=a.mib<=64 or not 1<=a.seconds<=30:
    p.error('mib must be 1..64; seconds must be 1..30')
print(f'PID={os.getpid()} mode={a.mode} duration={a.seconds}s',flush=True)
end=time.monotonic()+a.seconds
if a.mode=='memory':
    data=bytearray(a.mib*1024*1024)
    for i in range(0,len(data),4096):
        data[i]=1
    while time.monotonic()<end:
        time.sleep(0.1)
elif a.mode=='sleep':
    while time.monotonic()<end:
        time.sleep(0.001)
else:
    x=0
    while time.monotonic()<end:
        for i in range(10000):
            x=(x+i)%100003
print('负载已退出；已分配内存由进程退出回收。')
