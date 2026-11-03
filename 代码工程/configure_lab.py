"""按本人券有效期和实验限额生成配置；不读取或保存API Key。"""
import argparse
from datetime import datetime
import json
from pathlib import Path
from host import BASE,validate_config

def build_config(expiry,budget=1.0,requests=6):
    config=json.loads((BASE/'config.example.json').read_text())
    parsed=datetime.fromisoformat(expiry)
    if parsed.tzinfo is None or parsed<=datetime.now().astimezone():
        raise ValueError('有效期必须含时区且晚于当前时间，请按本人券详情填写。')
    config.update(coupon_expires_at=parsed.isoformat(),budget_cny=budget,max_total_requests=requests)
    validate_config(config)
    return config

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--coupon-expires',required=True,help='本人券截止时间，ISO格式含时区')
    ap.add_argument('--budget',type=float,default=1.0)
    ap.add_argument('--requests',type=int,default=6)
    ap.add_argument('--output',default='config.local.json')
    args=ap.parse_args()
    config=build_config(args.coupon_expires,args.budget,args.requests)
    with Path(args.output).open('x',encoding='utf-8') as f:
        json.dump(config,f,ensure_ascii=False,indent=2);f.write('\n')
    print('已写入本地配置。请先自行核对券适用产品、区域、计费方式和抵扣限制。')
    print('本程序不查询券余额，也不保证实际抵扣。API探测和Host均须使用 --config '+args.output)
