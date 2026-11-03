"""已提供：选做交互功能的安全回退，不影响主实验。"""
import json
from lab_common import StudentTaskPending
from students.interaction_helpers import summarize_evidence


def display_summary(trace):
    try:
        text=summarize_evidence(trace)
        if not isinstance(text,str) or len(text)>4000:raise ValueError('summary must be text <=4000 characters')
        return {'mode':'student_summary','text':text,'optional_task_pending':False}
    except StudentTaskPending as exc:
        return {'mode':'provided_json_fallback','text':json.dumps(trace,ensure_ascii=False),
                'optional_task_pending':True,'message':str(exc)}
    except Exception as exc:
        return {'mode':'provided_json_fallback','text':json.dumps(trace,ensure_ascii=False),
                'optional_task_pending':False,'extension_error':type(exc).__name__}
