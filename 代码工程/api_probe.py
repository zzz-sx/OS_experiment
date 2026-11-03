"""真实云端一次请求，验证 API；与 host.py 共用预算记录。"""
import argparse,asyncio,json,os
from pathlib import Path
from host import Model,BASE

async def main(config_path=None):
    if not os.environ.get('MAAS_API_KEY','').strip():
        raise SystemExit('请先配置 MAAS_API_KEY 环境变量。')
    config=json.loads((Path(config_path) if config_path else BASE/'config.example.json').read_text())
    model=Model(config)
    try:
        r=await model.request(dict(model=config['model'],stream=False,thinking={'type':'disabled'},
                 max_completion_tokens=100,messages=[{'role':'user','content':'请仅回复：操作系统实验接口连接成功。'}]))
        print(json.dumps(r,ensure_ascii=False,indent=2))
    finally:
        await model.close()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config');args=ap.parse_args()
    asyncio.run(main(args.config))
