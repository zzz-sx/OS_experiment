#!/usr/bin/env bash
# 已提供环境入口：只检查框架；不会要求尚未实现的OS实验全部通过。
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ "$(id -u)" = 0 ]; then
  echo '请使用普通实验用户，不使用root。' >&2
  exit 2
fi
LAB_PYTHON="${1:-python3.11}"
if ! command -v "$LAB_PYTHON" >/dev/null 2>&1; then
  echo '先安装独立Python3.11.16，将uv python find 3.11.16输出路径作为参数。' >&2
  exit 2
fi
"$LAB_PYTHON" -c 'import sys; assert sys.version_info[:3]==(3,11,16), "正式环境固定独立Python3.11.16"'
"$LAB_PYTHON" preflight.py --require-version 24.03
if [ -e .venv ]; then
  .venv/bin/python -c 'import sys; assert sys.version_info[:3]==(3,11,16), "已有.venv不符，另建项目目录"'
else
  "$LAB_PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip check
.venv/bin/python prepare_lab.py
mkdir -p evidence
.venv/bin/python -m pip freeze > evidence/pip-freeze.txt
.venv/bin/python -m unittest test_framework test_setup -v > evidence/framework-tests.log 2>&1
.venv/bin/python validate_lab.py --stage framework --require-openeuler --require-version 24.03
.venv/bin/python host.py --mock --output evidence/framework-host-demo.json
printf '%s\n' '框架与离线演示完成，未调用云模型。' '14个OS工具仍待学生实现；请分模块检查，不将框架就绪当作Project完成。'
