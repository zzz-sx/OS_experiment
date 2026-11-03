"""已提供的框架回归，不依赖学生实现全部OS接口，不调用真实云模型。"""
import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock
import host,lab_common,server
from lab_common import StudentTaskPending,result
from mcp_bridge import execute_tool
from model_gateway import BudgetLedger
from validate_lab import validate
from datetime import datetime,timedelta,timezone


class Infrastructure(unittest.TestCase):
    def test_pending_is_explicit_not_success(self):
        with patch.object(server.ops,'get_process_tree',side_effect=StudentTaskPending('P1','students/process.py')):
            value=server.get_process_tree()
        self.assertFalse(value['ok']);self.assertEqual(value['error'],'NOT_IMPLEMENTED')
        self.assertIsNone(value['data']);self.assertEqual(value['task'],'P1')

    def test_path_and_symlink_guard(self):
        with tempfile.TemporaryDirectory() as folder,tempfile.TemporaryDirectory() as outside:
            with patch.object(lab_common,'ROOT',Path(folder)):
                (Path(folder)/'escape').symlink_to(outside,target_is_directory=True)
                for path in ['../','escape']:
                    with self.assertRaises(ValueError):lab_common.safe_path(path)

    def test_own_process_guard(self):
        self.assertEqual(lab_common.own_process(os.getpid()).pid,os.getpid())
        with self.assertRaises(ValueError):lab_common.own_process(True)

    def test_unknown_tool_never_dispatches(self):
        session=type('Session',(),{'call_tool':AsyncMock()})()
        value=asyncio.run(execute_tool(session,{'function':{'name':'shell','arguments':'{}'}},{},1000,set()))
        self.assertFalse(value['ok']);session.call_tool.assert_not_called()

    def test_schema_error_never_dispatches(self):
        definitions={'top':{'parameters':{'type':'object','properties':{'limit':{'type':'integer','maximum':10}},'additionalProperties':False}}}
        value=asyncio.run(execute_tool(None,{'function':{'name':'top','arguments':'{"limit":999}'}},definitions,1000,set()))
        self.assertFalse(value['ok'])

    def test_pid_requires_earlier_evidence(self):
        definitions={'get_process_memory':{'parameters':{'type':'object','properties':{'pid':{'type':'integer'}}}}}
        value=asyncio.run(execute_tool(None,{'function':{'name':'get_process_memory','arguments':'{"pid":1}'}},definitions,1000,set()))
        self.assertFalse(value['ok'])

    def test_budget_is_persistent(self):
        config=dict(budget_cny=.3,per_request_reserve_cny=.2,max_total_requests=1,
            coupon_expires_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
            input_cny_per_million=.8,output_cny_per_million=1.6)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.sqlite';ledger=BudgetLedger(path,config);ident=ledger.reserve()
            self.assertAlmostEqual(ledger.settle(ident,{'prompt_tokens':2000,'completion_tokens':500}),.0024)
            ledger.db.close();ledger=BudgetLedger(path,config)
            with self.assertRaises(RuntimeError):ledger.reserve()
            ledger.db.close()

    def test_optional_helper_fallback(self):
        from presentation_helpers import display_summary
        with patch('presentation_helpers.summarize_evidence',side_effect=StudentTaskPending('N1','optional')):
            value=display_summary([])
        self.assertEqual(value['mode'],'provided_json_fallback');self.assertTrue(value['optional_task_pending'])

    def test_oversized_tool_result_preserves_error_contract(self):
        response=type('Response',(),{'isError':False,'structuredContent':result('test',{'blob':'x'*2000})})()
        session=type('Session',(),{'call_tool':AsyncMock(return_value=response)})()
        definitions={'sample':{'parameters':{'type':'object'}}}
        value=asyncio.run(execute_tool(session,{'function':{'name':'sample','arguments':'{}'}},definitions,512,set()))
        self.assertFalse(value['ok']);self.assertEqual(value['error'],'RESULT_TOO_LARGE')
        self.assertIn('sampled_at',value);self.assertIsNone(value['data'])


class EndToEnd(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_message_mapping_without_network(self):
        """用HTTP MockTransport核对真实模式的协议结构，禁止任何外网请求。"""
        import httpx,model_gateway
        requests=[];original_client=httpx.AsyncClient
        def respond(request):
            self.assertEqual(request.url.path,'/v2/chat/completions')
            self.assertEqual(request.headers['Authorization'],'Bearer TEST_ONLY_KEY')
            payload=json.loads(request.content);requests.append(payload)
            if len(requests)==1:
                self.assertEqual(payload['tool_choice'],'auto')
                self.assertIn('get_time',{t['function']['name'] for t in payload['tools']})
                message={'role':'assistant','content':'','tool_calls':[
                    {'id':'wire-1','type':'function','function':{'name':'get_memory_info','arguments':'{}'}}]}
            else:
                tool=[m for m in payload['messages'] if m['role']=='tool']
                self.assertEqual(tool[0]['tool_call_id'],'wire-1')
                self.assertTrue(json.loads(tool[0]['content'])['ok'])
                message={'role':'assistant','content':'测试传输已收到真实工具证据。'}
            return httpx.Response(200,json={'choices':[{'message':message}],
                'usage':{'prompt_tokens':10,'completion_tokens':5}})
        def offline_client(**kwargs):return original_client(transport=httpx.MockTransport(respond),**kwargs)
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);config=json.loads((host.BASE/'config.example.json').read_text())
            config['coupon_expires_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
            path=folder/'config.json';path.write_text(json.dumps(config))
            with patch.object(model_gateway,'BASE',folder),patch('model_gateway.httpx.AsyncClient',offline_client),patch.dict(os.environ,{'MAAS_API_KEY':'TEST_ONLY_KEY'}):
                report=await host.run('协议结构测试',mock=False,config_path=path,output=str(folder/'wire.json'))
        self.assertEqual(len(requests),2);self.assertEqual(report['status'],'completed')
        self.assertEqual(len(report['model_usage']),2)

    async def test_framework_real_mcp(self):
        with tempfile.TemporaryDirectory() as d:
            report=await validate(output=Path(d)/'framework.json',stage='framework')
        self.assertTrue(report['success']);self.assertEqual(len(report['tools']),16)
        self.assertEqual({k:len(v) for k,v in report['module_tools'].items()},{'memory':7,'filesystem':5,'process':6})

    async def test_mock_model_real_mcp(self):
        with tempfile.TemporaryDirectory() as d:
            report=await host.run('查询已提供示例',mock=True,output=str(Path(d)/'mock.json'))
        self.assertEqual(report['status'],'completed');self.assertEqual(report['evidence_count'],2)
        self.assertEqual({r['tool'] for r in report['trace']},{'get_time','get_memory_info'})

    async def test_pending_cannot_be_hidden_by_other_success(self):
        values=[result('datetime',{'timezone':'UTC'},kind='status'),result('student',error='NOT_IMPLEMENTED',kind='status')]
        with tempfile.TemporaryDirectory() as d,patch.object(host,'execute_tool',AsyncMock(side_effect=values)):
            report=await host.run('状态测试',mock=True,output=str(Path(d)/'pending.json'),mock_scenario='pending')
        self.assertEqual(report['status'],'not_implemented');self.assertEqual(report['evidence_count'],1)

    async def test_failure_keeps_evidence(self):
        original=host.Model.request
        async def fail_second(model,payload):
            if model.calls:raise RuntimeError('INJECTED_STOP')
            return await original(model,payload)
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'failure.json'
            with patch.object(host.Model,'request',fail_second):
                with self.assertRaises(Exception):await host.run('失败测试',mock=True,output=str(output))
            report=json.loads(output.read_text())
        self.assertEqual(report['status'],'failed');self.assertEqual(len(report['trace']),2)

    async def test_truncated_is_incomplete(self):
        original=host.Model.request
        async def truncated(model,payload):
            if model.calls:
                model.calls+=1
                return {'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'半句'}}]}
            return await original(model,payload)
        with tempfile.TemporaryDirectory() as d,patch.object(host.Model,'request',truncated):
            report=await host.run('截断测试',mock=True,output=str(Path(d)/'truncated.json'))
        self.assertEqual(report['status'],'truncated')

    async def test_empty_response_is_incomplete(self):
        async def empty(model,payload):return {'choices':[{'message':{'role':'assistant','content':''}}]}
        with tempfile.TemporaryDirectory() as d,patch.object(host.Model,'request',empty):
            report=await host.run('空正文测试',mock=True,output=str(Path(d)/'empty.json'))
        self.assertEqual(report['status'],'empty_response')


if __name__=='__main__':unittest.main()
