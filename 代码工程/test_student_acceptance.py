"""少量公开验收样例，无完整答案。未实现则skip；skip不等于模块完成。"""
import unittest
from lab_common import StudentTaskPending
from students.algorithms import page_replace,scheduler,disk_allocate
from students.memory import parse_smaps,analyze_memory_patterns


class StudentAcceptance(unittest.TestCase):
    def implemented(self,fn,*args,**kwargs):
        try:return fn(*args,**kwargs)
        except StudentTaskPending as exc:self.skipTest(str(exc))

    def test_single_frame_and_zero_page(self):
        result=self.implemented(page_replace,[0,0,1],1,'FIFO',42)
        self.assertEqual(result['faults'],2)
        self.assertEqual([r['hit'] for r in result['log']],[False,True,False])
        self.assertEqual(result['log'][-1]['evicted'],0)

    def test_arrival_and_idle(self):
        result=self.implemented(scheduler,[{'id':'A','arrival':2,'burst':1}],'FCFS')
        job=result['jobs'][0]
        self.assertEqual((job['response'],job['waiting'],job['turnaround']),(0,0,1))
        self.assertEqual(result['timeline'][0],{'id':'IDLE','start':0,'end':2})

    def test_allocate_block_zero_and_rollback(self):
        operations=[{'action':'create','name':'A','blocks':1},{'action':'create','name':'B','blocks':2}]
        result=self.implemented(disk_allocate,'contiguous',2,operations)
        self.assertEqual(result['log'][0]['map'][0],'A')
        self.assertFalse(result['log'][1]['success'])
        self.assertEqual(result['log'][0]['map'],result['log'][1]['map'])

    def test_smaps_units(self):
        text='00400000-00410000 r-xp 00000000 08:01 99 /usr/bin/demo\nSize: 64 kB\nRss: 20 kB\nPss: 10 kB\n'
        rows=self.implemented(parse_smaps,text)
        self.assertEqual(rows[0]['Rss_KiB'],20);self.assertEqual(rows[0]['Pss_KiB'],10)

    def test_no_reuse_has_null_interval(self):
        result=self.implemented(analyze_memory_patterns,[0,2,4])
        self.assertIsNone(result['data']['mean_reuse_interval'])


if __name__=='__main__':unittest.main()
