"""保留原操作单的样本准备入口，不实现学生的文件采集任务。"""
from prepare_fixtures import prepare
if __name__=='__main__':print('实验样本目录：',prepare())
