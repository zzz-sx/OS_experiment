"""学生本人补充测试。每模块至少一项反例/边界测试，不能只复制公开样例。"""
import unittest


class MyExperiments(unittest.TestCase):
    @unittest.skip('TODO：用本人内存反例替换此占位，写明独立预期与来源')
    def test_memory_case(self):
        raise NotImplementedError('TODO：例如设计有时间复用但页号不相邻的引用序列')

    @unittest.skip('TODO：用本人文件边界测试替换此占位')
    def test_filesystem_case(self):
        raise NotImplementedError('TODO：例如有界扫描截断/并发删除/容量不足回滚')

    @unittest.skip('TODO：用本人调度反例替换此占位')
    def test_process_case(self):
        raise NotImplementedError('TODO：例如时间片边界到达或CPU/IO交替的等待定义')
