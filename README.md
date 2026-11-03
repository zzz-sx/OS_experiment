# OS_experiment

MCP 与 openEuler 操作系统实验。基于课程提供的学生框架部署到 openEuler 24.03，并接入 DeepSeek 完成第八周基础工具的自然语言调用。

## 两个版本

| 版本 | 内容 | 查看 |
| --- | --- | --- |
| 课程原始版 | 从原始 `openEuler_MCP代码框架.zip` 提取的 44 个工程文件，未修改 | [course-original](https://github.com/zzz-sx/OS_experiment/tree/course-original) |
| 当前云端备份 | 2026-11-03 读取的云端工程，包含代码、验收证据和样本数据 | [week8-current-20261103](https://github.com/zzz-sx/OS_experiment/tree/week8-current-20261103) |

先提交原始版，再提交当前版，保留仓库最初的提交历史。

- [原始版与当前版逐行对比](https://github.com/zzz-sx/OS_experiment/compare/course-original...week8-current-20261103)
- [修改说明](修改说明.md)
- [工程源码](代码工程/)
- [验收证据](代码工程/evidence/)

## 当前保留的代码改动

修改 `host.py`、`model_gateway.py`、工程 `README.md`；新增 `config.deepseek.example.json`。
基础 Server、工具实现、MCP 桥接和学生模块沿用原始代码。第八周通信与基础自然语言调用已留证，后续学生模块仍有 TODO。

```bash
cd 代码工程
source .venv/bin/activate
python mcp_check.py get_time
python host.py "请查询服务器当前 UTC 时间，并注明数据来源。" --config config.deepseek.example.json --output evidence/deepseek.json
```

运行真实模型前，在当前终端设置 `DEEPSEEK_API_KEY`。仓库中的密钥位置留空。
Python 固定 3.11.16，依赖见工程内 `requirements-lock.txt`，环境安装步骤见 `bootstrap_env.sh`。

## 备份范围

保留云端工程代码、依赖清单、原始验收 JSON、运行日志和 `lab-data` 样本。
虚拟环境、缓存、运行状态数据库、私钥和私人配置不纳入 Git；虚拟环境通过依赖文件重建。
上传副本中的实际 API 密钥会清空，云端运行文件不受影响。
历史日志中的测试数量、版本与结论对应各自运行时间，不代表当前代码已完成后续全部模块。

工程原有 `.gitignore` 忽略新生成的 `evidence/` 与 `lab-data/`。本次已将检查过的快照文件纳入版本；以后新增验收文件，需要检查内容后显式添加这些目录。
