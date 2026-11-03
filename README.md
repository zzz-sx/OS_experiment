# OS_experiment

MCP 与 openEuler 操作系统实验，当前使用课程原版代码和华为云 MaaS 的 `openpangu-2.0-flash`。

## 当前分支

- `main`：保留最初课程代码。
- `week8-evidence-cleanup`：当前待验收版本，不合并 main。
- 此前 DeepSeek 直连接入保留在历史提交及 `week8-deepseek` 分支，当前工程已移除其适配。

## 相比原版

44 个原始工程文件全部保留；Python 源码与原版完全一致。
唯一工程配置改动是 `代码工程/config.example.json` 的 `max_total_requests` 从6改为100。
原版预算、有效期和次数检查完整保留，未绕过。

## 使用 MaaS 验收

先在华为云 MaaS 开通 `openPangu-2.0-Flash`，创建 MaaS API Key。
在云机同一个 Bash 终端设置环境变量，等号和引号使用英文半角：

```bash
cd ~/oslab2403/代码工程
source .venv/bin/activate
export MAAS_API_KEY="替换为你的实际MaaS_API_Key"
python api_probe.py > evidence/api-probe.json
python host.py "请查询服务器当前 UTC 时间，并注明数据来源。" --output evidence/maas.json
```

`api_probe.py` 检查真实模型接口；`host.py` 检查真实模型经 MCP 调用工具。
成功时 Host 结果文件的 `mode=cloud_llm_real_mcp`、`status=completed`，并包含成功的工具 trace。
测试会产生模型费用；次数100指 API 请求次数，一次提问通常包含多次请求。
原版配置还保留1元本地估算预算、单次最多4次模型请求及配置有效期。

## 已验证与待验证

21 项原版基础测试、openEuler 24.03/MCP 离线检查通过。
原版账本已验证允许100次，在第101次拒绝，重开账本仍生效。
MaaS 真实调用需要用户设置自己的 Key 后执行；本次恢复没有发送付费请求。

验收记录保存在 `代码工程/evidence/`。虚拟环境、样本、密钥和账本不提交 Git。
代码恢复前的私有备份保存在云机工程目录之外。历史 DeepSeek 成功记录不作为当前 MaaS 验收证据。

[与原版比较](https://github.com/zzz-sx/OS_experiment/compare/main...week8-evidence-cleanup)
