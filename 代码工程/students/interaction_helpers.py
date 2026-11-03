"""交互部分的选做辅助任务。未完成时Host有明确的默认JSON展示，不阻塞主链路。"""
from lab_common import StudentTaskPending


def summarize_evidence(trace: list[dict]) -> str:
    """【TODO N1 选做】把工具trace整理成简短的可读证据索引。

    输入来自Host已校验的trace；建议包含工具名、采样时间、真实/模拟类型、
    成功或错误、原始证据定位。仅整理已有数据，不能补写推测值或重发请求。
    返回纯文本<=4000字符，不渲染HTML，不读取Key；不需要再次连接模型。
    Host已提供JSON回退，N1未实现不会导致实验停止。
    """
    raise StudentTaskPending('N1','students/interaction_helpers.py:summarize_evidence')


def export_report_markdown(report: dict) -> str:
    """【TODO N2 选做】生成报告草稿文本，保留失败/待实现标记与证据引用。

    输入是Host报告字典，输出Markdown字符串；不覆盖原JSON，不写盘，不泄漏凭据。
    真实数据、模拟、模型原文、人工分析分别设置区域；人工纠错留空供本人填写。
    此函数供学生自行接到导出按钮/命令中，CLI与Web基础链路不依赖它。
    """
    raise StudentTaskPending('N2','students/interaction_helpers.py:export_report_markdown')
