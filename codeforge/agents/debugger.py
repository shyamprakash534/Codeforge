"""Debugger agent: captures actionable failure context and controls retries."""
from codeforge.core.state import TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector
class DebuggerAgent:
    def run(self,state:TaskState,tracer:TraceCollector)->TaskState:
        span=tracer.start_span('agent.debugger',span_type='agent'); state.phase=TaskPhase.DEBUG
        if state.test_results and not state.test_results.is_success:
            state.retry_count += 1
            detail=(state.test_results.stderr or state.test_results.stdout or 'Unknown test failure').strip()
            state.log(f'Debug attempt {state.retry_count}/{state.max_retries}: {detail[-1000:]}')
        else: state.log('No test failure requiring debugging.')
        tracer.end_span(span.span_id); return state
