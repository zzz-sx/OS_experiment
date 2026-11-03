"""已提供：工具定义映射、Host参数/PID验证与MCP调用，不包含操作系统答案。"""
import asyncio,json
from jsonschema import Draft202012Validator
from model_gateway import encode
from lab_common import result

def tool_definitions(tools):
    out = []
    for t in tools:
        schema = dict(t.inputSchema)
        schema['additionalProperties'] = False
        out.append(dict(type='function',function=dict(name=t.name,description=t.description or '',parameters=schema)))
    return out

async def execute_tool(session,call,definitions,max_bytes,known_pids):
    try:
        if not isinstance(call,dict) or not isinstance(call.get('function'),dict):
            raise ValueError('MALFORMED_TOOL_CALL')
        if call.get('type','function')!='function': raise ValueError('UNKNOWN_TOOL_TYPE')
        fn=call['function']; name=fn.get('name')
        if name not in definitions:
            raise ValueError('UNKNOWN_TOOL')
        arg_text = fn.get('arguments','{}')
        if not isinstance(arg_text,str) or len(arg_text.encode()) > 8192:
            raise ValueError('ARGUMENTS_TOO_LARGE_OR_NOT_STRING')
        args = json.loads(arg_text)
        Draft202012Validator(definitions[name]['parameters']).validate(args)
        if name in {'get_process_memory','monitor_context_switches','sample_process_memory','get_process_schedstat'} and args.get('pid') is not None and args['pid'] not in known_pids:
            raise ValueError('PID must come from earlier tool evidence in this run')
        response = await asyncio.wait_for(session.call_tool(name,args),timeout=15)
        if response.isError:
            raise ValueError('MCP_TOOL_ERROR: '+str(response.content)[:240])
        value = response.structuredContent
        if not value:
            text = '\n'.join(x.text for x in response.content if getattr(x,'type','')=='text')
            value = json.loads(text)
        # v1 FastMCP may wrap a primitive return; dict returns are normally direct.
        if isinstance(value,dict) and set(value)=={'result'} and isinstance(value['result'],dict):
            value=value['result']
        if not isinstance(value,dict): raise ValueError('MALFORMED_TOOL_RESULT')
        if value.get('ok') and name in {'list_top_processes','get_process_tree'}:
            data = value.get('data',{})
            for row in data.get('processes',data.get('nodes',[])):
                known_pids.add(row['pid'])
        text = encode(value)
        if len(text.encode()) > max_bytes:
            value = result('Host result size guard',kind='status',error='RESULT_TOO_LARGE',
                         limitations=['请缩小采样范围或日志长度，未把截断数据当完整证据。'])
        return value
    except Exception as exc:
        return result('Host tool validation',kind='status',error=f'{type(exc).__name__}: {str(exc)[:300]}')
