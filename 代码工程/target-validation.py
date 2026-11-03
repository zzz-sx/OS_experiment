"""兼容原入口。默认只检查framework；完整验收请显式--stage all。"""
import runpy
if __name__=='__main__':runpy.run_module('validate_lab',run_name='__main__')
