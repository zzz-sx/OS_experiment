"""无需第三方包的只读环境检查；可用旧系统Python执行。"""
from __future__ import print_function
import argparse,json,os,platform,shutil,sys
from pathlib import Path
def release_fields(text):
    fields={}
    for line in text.splitlines():
        if '=' in line and not line.startswith('#'):
            key,value=line.split('=',1)
            fields[key]=value.strip().strip('\"\'')
    return fields

def require_release(text,version):
    fields=release_fields(text)
    if fields.get('ID','').lower()!='openeuler':
        raise ValueError('需要真正的openEuler系统，HCE或容器名称不能代替系统验收。')
    actual=fields.get('VERSION_ID','')
    if actual!=version:
        raise ValueError('需要openEuler %s，实际VERSION_ID=%s；先检查所选镜像。'%(version,actual))
    return fields

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--require-version',help='严格检查/etc/os-release中的VERSION_ID，如24.03')
    args=ap.parse_args()
    p=Path('/etc/os-release');root=Path(__file__).resolve().parent
    release=p.read_text() if p.exists() else ''
    if args.require_version:
        try: require_release(release,args.require_version)
        except ValueError as exc: raise SystemExit(str(exc))
    print(json.dumps({'python':sys.version,'executable':sys.executable,'kernel':platform.release(),'architecture':platform.machine(),
                      'os_release':release,'release_fields':release_fields(release),
                      'uid':os.getuid() if hasattr(os,'getuid') else None,
                      'disk_free_bytes':shutil.disk_usage(str(root)).free,'python311':shutil.which('python3.11'),'uv':shutil.which('uv'),
                      'cloud_key_configured':bool(os.environ.get('MAAS_API_KEY'))},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
