"""学生本人补充测试。每模块至少一项反例/边界测试，不能只复制公开样例。"""
import unittest
import random
from types import SimpleNamespace
from unittest.mock import Mock,patch
from lab_common import psutil,StudentTaskPending
from students import memory
from students.algorithms import page_replace,REFERENCE


class MyExperiments(unittest.TestCase):
    def test_memory_case(self):
        # 同页间隔均为2，但相邻访问页号差99：时间复用不等于相邻页号。
        data=memory.analyze_memory_patterns([1,100,1,100])['data']
        self.assertEqual((data['distinct_pages'],data['repeated_references']),(2,2))
        self.assertEqual(data['mean_reuse_interval'],2)
        self.assertEqual(data['adjacent_page_ratio'],0)

    def test_memory_single_reference_and_invalid_pages(self):
        data=memory.analyze_memory_patterns([0])['data']
        self.assertIsNone(data['mean_reuse_interval'])
        self.assertEqual(data['adjacent_page_ratio'],0)
        for pages in [[],[True],[-1],[4096],[1.5],[0]*129,'010']:
            with self.subTest(pages=pages),self.assertRaises(ValueError):
                memory.analyze_memory_patterns(pages)

    def test_memory_smaps_missing_fields_anonymous_and_limit(self):
        text=('1000-2000 rw-p 00000000 00:00 0\nSize: 4 kB\nRss: 0 kB\n'
              '2000-3000 r--p 00000000 08:01 1 /private/path/file name\nPss: 2 kB\n'
              '3000-4000 rw-p 00000000 00:00 0 [heap]\nPrivate_Dirty: 4 kB\n')
        rows=memory.parse_smaps(text)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['label'],'[anonymous]')
        self.assertNotIn('Pss_KiB',rows[0])
        self.assertEqual(rows[1]['label'],'file name')
        self.assertEqual(rows[2]['Private_Dirty_KiB'],4)
        self.assertEqual(memory.parse_smaps(text,1),rows[:1])
        self.assertEqual(memory.parse_smaps(''),[])

    def test_memory_stat_comm_with_spaces_and_parentheses(self):
        # state为第3字段，minflt=17、majflt=29；comm中的空格和右括号不能移位。
        text='123 (name (with ) spaces)) S 1 2 3 4 5 6 17 8 29 10\n'
        with patch.object(memory.Path,'read_text',return_value=text):
            self.assertEqual(memory.read_proc_faults(123),dict(minor_faults=17,major_faults=29))
        with patch.object(memory.Path,'read_text',return_value='123 (short) S 1'):
            with self.assertRaises(ValueError):memory.read_proc_faults(123)

    def test_memory_top_processes_uid_sort_and_exit(self):
        def process(pid,rss,uid):
            proc=Mock(pid=pid)
            proc.uids.return_value=SimpleNamespace(real=uid)
            proc.memory_info.return_value=SimpleNamespace(rss=rss)
            proc.name.return_value='demo';proc.ppid.return_value=1
            return proc
        small=process(10,100,1000);large=process(20,300,1000)
        foreign=process(30,900,2000);gone=process(40,500,1000)
        gone.memory_info.side_effect=psutil.NoSuchProcess(40)
        with patch.object(memory.os,'getuid',return_value=1000,create=True), \
             patch.object(memory.psutil,'process_iter',return_value=[small,foreign,gone,large]), \
             patch.object(memory,'_check_identity'):
            data=memory.list_top_processes(1)['data']
        self.assertEqual([row['pid'] for row in data['processes']],[20])
        self.assertEqual(data['excluded'],2)
        foreign.memory_info.assert_not_called()

    def test_memory_identity_rejects_pid_reuse(self):
        proc=Mock(pid=123);proc.is_running.return_value=True
        replacement=Mock();replacement.create_time.return_value=2
        with patch.object(memory,'own_process',return_value=replacement):
            with self.assertRaises(psutil.NoSuchProcess):memory._check_identity(proc,1)
        proc.status.return_value=psutil.STATUS_ZOMBIE
        replacement.create_time.return_value=1
        with patch.object(memory,'own_process',return_value=replacement):
            with self.assertRaises(psutil.NoSuchProcess):memory._check_identity(proc,1)

    def test_memory_smaps_read_cap_and_partial(self):
        first=b'1000-2000 rw-p 00000000 00:00 0\nRss: 4 kB\n'
        second=b'2000-3000 rw-p 00000000 00:00 0\nRss: 8 kB\n'
        proc=Mock(pid=123);proc.name.return_value='demo'
        proc.memory_info.return_value=SimpleNamespace(_asdict=lambda:{'rss':4096})
        with patch.object(memory,'own_process',return_value=proc), \
             patch.object(memory,'_check_identity'),patch.object(memory.platform,'system',return_value='Linux'), \
             patch.object(memory.Path,'open') as opened:
            stream=opened.return_value.__enter__.return_value
            stream.read.return_value=first+second
            data=memory.get_process_memory(123,1)['data']
            self.assertTrue(data['maps_partial'])
            self.assertEqual(len(data['maps']),1)
            stream.read.assert_called_with(2_000_000)
            data=memory.get_process_memory(123,2)['data']
            self.assertFalse(data['maps_partial'])
            stream.read.return_value=(first+second).ljust(2_000_000,b' ')
            data=memory.get_process_memory(123,2)['data']
            self.assertTrue(data['maps_partial'])
            self.assertEqual([row['Rss_KiB'] for row in data['maps']],[4])

    def test_memory_smaps_permission_error_is_not_zero_success(self):
        proc=Mock(pid=123)
        with patch.object(memory,'own_process',return_value=proc), \
             patch.object(memory.platform,'system',return_value='Linux'), \
             patch.object(memory.Path,'open',side_effect=PermissionError('smaps denied')):
            with self.assertRaises(PermissionError):memory.get_process_memory(123)

    def test_memory_sample_actual_interval_and_rss_decrease(self):
        proc=Mock(pid=123)
        proc.memory_info.side_effect=[SimpleNamespace(rss=100),SimpleNamespace(rss=80)]
        with patch.object(memory,'own_process',return_value=proc),patch.object(memory,'_check_identity'), \
             patch.object(memory.platform,'system',return_value='Linux'), \
             patch.object(memory.psutil,'swap_memory',side_effect=[SimpleNamespace(sin=10,sout=20),SimpleNamespace(sin=13,sout=25)]), \
             patch.object(memory,'read_proc_faults',side_effect=[dict(minor_faults=7,major_faults=1),dict(minor_faults=9,major_faults=1)]), \
             patch.object(memory.time,'monotonic',side_effect=[10,10.25]),patch.object(memory.time,'sleep') as sleep:
            data=memory.sample_process_memory(123,2,.1)['data']
        self.assertEqual(data['delta'],dict(rss_bytes=-20,system_swap_in_bytes=3,
            system_swap_out_bytes=5,minor_faults=2,major_faults=0,elapsed_seconds=.25))
        self.assertTrue(all(row['sampled_at'].endswith('+00:00') for row in data['samples']))
        sleep.assert_called_once_with(.1)

    def test_memory_sample_rejects_counter_rollback(self):
        proc=Mock(pid=123);proc.memory_info.return_value=SimpleNamespace(rss=100)
        with patch.object(memory,'own_process',return_value=proc),patch.object(memory,'_check_identity'), \
             patch.object(memory.platform,'system',return_value='Linux'), \
             patch.object(memory.psutil,'swap_memory',return_value=SimpleNamespace(sin=0,sout=0)), \
             patch.object(memory,'read_proc_faults',side_effect=[dict(minor_faults=7,major_faults=1),dict(minor_faults=6,major_faults=1)]), \
             patch.object(memory.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'counter decreased'):memory.sample_process_memory(123,2,.1)

    def test_page_short_hand_calculation(self):
        pages=[0,1,2,0,3,0,4]
        for algorithm,expected in [('FIFO',6),('LRU',5),('CLOCK',6),('OPT',5)]:
            with self.subTest(algorithm=algorithm):
                data=page_replace(pages,3,algorithm)
                self.assertEqual(data['faults'],expected)
                self.assertEqual(data['faults'],sum(not row['hit'] for row in data['log']))
        fifo=page_replace(pages,3,'FIFO')['log']
        self.assertEqual(fifo[4]['evicted'],0)
        self.assertEqual(fifo[-1]['frames'],[3,0,4])

    def test_page_default_reference_counts(self):
        for algorithm,expected in [('FIFO',10),('LRU',9),('OPT',7)]:
            with self.subTest(algorithm=algorithm):
                self.assertEqual(page_replace(REFERENCE,3,algorithm)['faults'],expected)

    def test_page_fifo_belady_counterexample(self):
        # 经典引用串手算：FIFO增加页框后，缺页从9增加到10。
        pages=[1,2,3,4,1,2,5,1,2,3,4,5]
        self.assertEqual(page_replace(pages,3,'FIFO')['faults'],9)
        self.assertEqual(page_replace(pages,4,'FIFO')['faults'],10)

    def test_page_clock_bits_and_hand(self):
        rows=page_replace([0,1,2,0,3],3,'CLOCK')['log']
        self.assertEqual(rows[3]['hand'],0)
        self.assertEqual(rows[4]['cleared_slots'],[0,1,2])
        self.assertEqual(rows[4]['reference_bits'],[1,0,0])
        self.assertEqual(rows[4]['hand'],1)

    def test_page_single_frame_repeated_and_snapshot_copy(self):
        for algorithm in ['FIFO','LRU','CLOCK','OPT','RANDOM']:
            with self.subTest(algorithm=algorithm):
                rows=page_replace([0,0,1,1],1,algorithm)['log']
                self.assertEqual([row['hit'] for row in rows],[False,True,False,True])
                self.assertEqual(rows[2]['evicted'],0)
                self.assertEqual(rows[0]['frames'],[0])

    def test_page_random_repeatable_local_generator(self):
        state=random.getstate()
        first=page_replace([0,1,2,3,4],3,'RANDOM',42)
        self.assertEqual(random.getstate(),state)
        self.assertEqual(first,page_replace([0,1,2,3,4],3,'RANDOM',42))
        self.assertEqual([row['evicted'] for row in first['log']],[None,None,None,2,0])
        self.assertEqual(first['selected_algorithm'],'RANDOM')

    def test_page_random_compared_with_opt_on_two_sequences(self):
        for pages in [[0,1,2,0,3,0,4],REFERENCE]:
            with self.subTest(pages=pages):
                data=page_replace(pages,3,'RANDOM',42)
                self.assertGreaterEqual(data['faults'],page_replace(pages,3,'OPT')['faults'])
                self.assertLessEqual(data['faults'],len(pages))

    def test_page_invalid_input_and_unimplemented_strategies(self):
        for pages in [[],[False],[-1],[4096],[0]*129]:
            with self.subTest(pages=pages),self.assertRaises(ValueError):page_replace(pages)
        for args in [([0],0),([0],True),([0],3,'invalid'),([0],3,'RANDOM',-1)]:
            with self.subTest(args=args),self.assertRaises(ValueError):page_replace(*args)
        for algorithm in ['SECOND_CHANCE','HYBRID']:
            with self.subTest(algorithm=algorithm),self.assertRaises(StudentTaskPending):page_replace([0],3,algorithm)

    @unittest.skip('TODO：用本人文件边界测试替换此占位')
    def test_filesystem_case(self):
        raise NotImplementedError('TODO：例如有界扫描截断/并发删除/容量不足回滚')

    @unittest.skip('TODO：用本人调度反例替换此占位')
    def test_process_case(self):
        raise NotImplementedError('TODO：例如时间片边界到达或CPU/IO交替的等待定义')
