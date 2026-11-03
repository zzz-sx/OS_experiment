# OS_experiment

MCP 与 openEuler 操作系统实验。基于课程提供的学生框架部署到 openEuler 24.03，并接入 DeepSeek 完成第八周基础工具的自然语言调用。

## 两个版本

| 版本 | 内容 | 查看 |
| --- | --- | --- |
| 课程原始版 | 从原始 `openEuler_MCP代码框架.zip` 提取的 44 个工程文件，未修改 | [main](https://github.com/zzz-sx/OS_experiment/tree/main) |
| 当前待验收版 | 2026-11-03 清理后的云端工程，只保留必要验收记录 | [week8-evidence-cleanup](https://github.com/zzz-sx/OS_experiment/tree/week8-evidence-cleanup) |

`main` 保留课程原始版；`week8-deepseek` 保留接入版本，本次清理独立放在 `week8-evidence-cleanup`。用户确认验收通过后再合并。
后续每次改动使用新的分支，验收前不直接写入 `main`。
`course-original` 和 `week8-current-20261103` 标签保留原始及首次云端快照，便于回溯。

- [本次清理差异](https://github.com/zzz-sx/OS_experiment/compare/week8-deepseek...week8-evidence-cleanup)
- [原始版与当前分支逐行对比](https://github.com/zzz-sx/OS_experiment/compare/main...week8-evidence-cleanup)
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

运行真实模型前，在当前终端设置 `DEEPSEEK_API_KEY`，或在云机私有副本的 `model_gateway.py` 顶部填写同名常量。仓库中的密钥位置留空。
Python 固定 3.11.16，依赖见工程内 `requirements-lock.txt`，环境安装步骤见 `bootstrap_env.sh`。

## 备份范围

保留云端工程代码、依赖清单和以下七份验收记录：

| evidence 文件 | 用途 |
| --- | --- |
| `tools-list.json` | 工具发现和输入 Schema |
| `get-time.json` | 成功调用的原始响应 |
| `reject-path.json` | 越界请求被拒绝的原始响应 |
| `framework-validation.json` | openEuler 24.03 与基础 MCP 验证 |
| `framework-tests.log` | 当前课程框架的 21 项基础测试结果 |
| `mock.json` | 离线模型、真实 MCP 的 Host 记录 |
| `deepseek.json` | 此前成功的真实 DeepSeek 调用记录，未因清理重新付费调用 |

重复目录、旧汇总、补充回归日志、调试日志与可生成的 `lab-data` 样本已清理。
后续文件模块如需样本，可在云机工程中执行 `python prepare_lab.py` 重新生成；样本不提交 Git。
虚拟环境、缓存、运行状态数据库、私钥和私人配置不纳入 Git；虚拟环境通过依赖文件重建。
上传副本中的实际 API 密钥会清空，云端运行文件不受影响。
历史日志中的测试数量、版本与结论对应各自运行时间，不代表当前代码已完成后续全部模块。

工程原有 `.gitignore` 忽略新生成的 `evidence/` 与 `lab-data/`。七份验收文件已单独纳入版本；以后新增验收记录，检查内容后显式添加所需文件。
