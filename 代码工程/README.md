# MCP 与 openEuler 操作系统实验学生框架

本版把操作系统采集和算法作为学生的主要实现任务。MCP连接、华为云模型适配、多轮工具调用、参数校验、基础前端和费用限制已提供。先让框架独立通过，再逐个完成学生模块。

一人一组，实验持续第6—13周，第8/11/13周验收框架通信、三个模块、自然语言集成。使用本人账号和代金券，自行核价开通，无需逐项找教师审批。

## 1 已提供和需要完成什么

|位置|代码状态|学生主要工作|
|---|---|---|
|students/memory.py|提供get_memory_info示例，其余TODO|进程RSS与映射、引用模式、时序采样|
|students/filesystem.py|接口与权限边界，采集主体TODO|容量/inode、文件分布、inotify事件|
|students/process.py|接口与采样约束，主体TODO|进程树、切换频率、CPU区间、等待统计|
|students/algorithms.py|签名、契约和样例输入，算法TODO|页面置换、磁盘分配、CPU调度|
|server.py / os_tools.py|已提供|阅读注册与模块调用关系，沿用既定接口|
|host.py|已提供多轮调用主线|理解请求、工具选择、结果回传和停止条件|
|model_gateway.py / mcp_bridge.py|已提供API、预算与协议支持|按本人配置使用，无需从零实现|
|students/interaction_helpers.py|两个选做TODO|可读证据索引、Markdown报告导出|
|presentation_helpers.py / web_ui.py|已提供默认展示和基础页面|选做增强，不阻塞OS实验|

统一注册16个工具。其中get_time及真实内存快照已提供，另外14个OS工具待实现。算法的MCP包装函数已经提供，算法本体仍是TODO。详见“模块保留与学生任务.md”。本包不包含原完整算法/采集答案或教师旧代码的压缩副本。

## 2 目录及调用关系

```text
代码工程/
  students/                    主要学生实现区
    memory.py filesystem.py process.py algorithms.py
    interaction_helpers.py     自然语言交互的选做辅助
  server.py                    16个工具注册与统一错误包装
  os_tools.py                  兼容原接口的统一门面
  memory_server.py filesystem_server.py process_server.py
  host.py                      自然语言请求和多轮执行主线
  mcp_bridge.py                tools映射、参数/PID校验、MCP调用
  model_gateway.py             华为云HTTP调用和持久预算
  lab_common.py                统一结果、路径/PID边界、TODO异常
  web_ui.py                    基础自然语言网页，默认仅回环监听
  validate_lab.py               框架及分模块验收入口
  experiments.py               两组参数对照及JSON/CSV/HTML留证
  test_framework.py test_setup.py
  test_student_acceptance.py test_student_custom.py
```

学生电脑以SSH连接openEuler云机。云机中的Host内置MCP Client，通过stdio启动Server，Server调用students中的代码。Host通过HTTPS调用华为云模型，模型返回tool_calls，Host校验后调用MCP，再用role=tool和同一tool_call_id回传结果。MCP Server不接收模型API Key，也不开放公网MCP端口。

## 3 环境与首次启动

正式目标沿用已冻结基线：openEuler24.03 LTS x86_64、普通用户、独立Python3.11.16、官方MCP SDK1.30.0。SDK要求Python>=3.10；不改系统Python。依赖按requirements-lock.txt安装，不执行无版本约束的升级。

本包的release-code.zip内顶层仍为“代码工程”，可沿用旧操作单的上传和解压命令。首次部署应使用新目录，避免覆盖个人源码。以下命令在云机工程目录执行：

```bash
python3 preflight.py --require-version 24.03
# 已安装uv与独立Python3.11.16时，使用实际找到的解释器路径
bash bootstrap_env.sh "$(~/.local/bin/uv python find 3.11.16)"
source .venv/bin/activate
```

bootstrap只运行框架回归、工具发现、get_time/内存示例和离线模型演示，不调用付费模型，也不要求学生TODO先完成。网络、/32安全组、SSH普通用户、公钥及uv安装步骤仍参照已有操作单；本版不修改这些云端资源。

已具备依赖环境时，可以按下列步骤独立验证：

```bash
python prepare_lab.py
python -m unittest test_framework test_setup -v
python validate_lab.py --stage framework
python mcp_check.py --list
python mcp_check.py get_time --unwrap
python host.py --mock --output evidence/framework-host-demo.json
```

预期：框架检查status=passed、16工具可发现；离线Host的status=completed，实际调用get_memory_info和get_time。这里只模拟模型响应，MCP通信和两个工具真实执行；不理解任意自然语言、不代表华为云推理成功。

## 4 未实现时的正确现象

```bash
python mcp_check.py get_process_tree --unwrap
python host.py --mock --mock-scenario pending --output evidence/pending-demo.json
```

新框架中第一条返回ok=false、error=NOT_IMPLEMENTED、task=P1、location指向学生文件，退出码2。第二条会收到真实工具的“待实现”结果，整体status=not_implemented，退出码2；同时保留成功调用的证据。学生完成相关功能后，该演示可能变为完成，不能通过写死状态维持“待实现”。

TODO统一抛出StudentTaskPending(task,location)，由Server封装；不要返回空字典、成功的0或编造数据。直接调用纯算法/学生函数会看到此异常，适合调试。

## 5 学生开发与分模块验证

建议先M1，再M2/M3/M4；文件F1/F2/F3；进程P1/P2/P3/P4；算法A1/A2/A3可用纯函数输入独立推进。各模块无需等待其他模块实现。具体输出字段和边界写在函数docstring，统一结果见接口契约.md。

```bash
# 按已完成的模块选择执行。尚有TODO时退出2并列出任务。
python validate_lab.py --stage memory
python validate_lab.py --stage filesystem
python validate_lab.py --stage process
# 正式openEuler验收增加目标版本限制
python validate_lab.py --stage all --require-openeuler --require-version 24.03
```

基础算法验收覆盖FIFO/LRU/CLOCK/OPT、连续/链接/索引、FCFS/SJF/RR。进阶增加RANDOM/SECOND_CHANCE/HYBRID和MLFQ，使用--advanced。已有Schema保留这些策略名，未实现某策略须明确报TODO，不得悄悄替换为其他算法。

```bash
python -m unittest test_student_acceptance -v
python -m unittest test_student_custom -v
python experiments.py --module memory
python experiments.py --module filesystem
python experiments.py --module process
```

公开验收小样例在未实现时显示skipped，不算模块完成。个人测试模板也故意标skip；请替换为本人有独立预期的反例。阶段完成以validate_lab模块结果和本人证据为准，不能只看unittest末尾的OK。

experiments默认每模块至少两组参数，结果写evidence/experiments，TODO单独留证并退出2，不画假成功图。--controlled仅在隔离Linux普通用户下显式启用；先确认采样接口可用，再执行有界负载，最多两子进程、每组3秒、内存16MiB，结束回收本人子进程。workload.py是提供的输入发生器，不向MCP暴露。

## 6 华为云模型和基础前端

现有配置沿用2026-10-14核实的MaaS V2、openpangu-2.0-flash与Bearer鉴权；本次不宣称重新核验实时价格、账户权限或完成云调用。当前账号的可用服务、价格和代金券抵扣仍需本人核对。config.example.json的期限和估价只作格式示例，不能套用到本人券。

```bash
read -r -p "本人券截止时间（ISO格式，含时区）: " LAB_EXPIRY
python configure_lab.py --coupon-expires "$LAB_EXPIRY" --budget 1 --requests 6
read -r -s -p "MaaS API Key: " MAAS_API_KEY
printf '\n'
export MAAS_API_KEY
mkdir -p evidence
python api_probe.py --config config.local.json > evidence/api-probe.json
# 首次只用已提供的快照验证模型工具闭环
python host.py "查询当前内存快照并说明证据局限。" \
  --config config.local.json --output evidence/cloud-demo.json
unset MAAS_API_KEY
```

完成OS接口后再提出高RSS进程、文件或调度诊断题。模型选择了尚未实现的工具时，报告会如实显示not_implemented。此时应先开发接口；不要反复消耗付费请求来测试TODO。累计6请求与估算预算1元只是首次个人实验配置，可按本人核验的预算调整；重启不能清除state/budget.sqlite计数，应用预算不控制ECS等费用，也不等于账户自动停费。

```bash
python web_ui.py
# 真实模型模式需要先export Key，且共用同一账本
python web_ui.py --cloud --config config.local.json
```

基础网页与CLI共用host.run；网页本机地址为127.0.0.1:8765。远程浏览需SSH转发权限，原历史实例此路径未通过，CLI为主路径。不要开放8765公网入方向或绕开sshd策略。EulerCopilot、Streamable HTTP沿用选做扩展范围。

## 7 提交与验证范围

每人提交自己的students源码、个人测试、依赖锁文件、运行说明、原始JSON与参数对照、报告、未完成清单；自然语言任务另存trace、usage、模型原文和人工纠错。每模块需要真实观测、模拟或受控比较及解释，不能仅把所有TODO改成固定返回值。

不提交.venv、lab-data样本、缓存、state账本、个人config、Key、私钥。运行时间、单位、来源及真实/模拟标记应完整。新框架的本次验证见外层“验证说明.md”；历史完整答案版的48测试/28调用不能作为本框架或学生实现的通过记录。
