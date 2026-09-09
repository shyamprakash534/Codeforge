"""Debugger agent: turns test failures into bounded repair suggestions."""
import json, re
from codeforge.core.state import TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector
from codeforge.llm.ollama import OllamaClient

class DebuggerAgent:
    def __init__(self, repo_path:str, llm=None):
        self.repo_path=repo_path; self.llm=llm
    def run(self,state:TaskState,tracer:TraceCollector)->TaskState:
        span=tracer.start_span('agent.debugger',span_type='agent'); state.phase=TaskPhase.DEBUG
        try:
            if not state.test_results or state.test_results.is_success:
                state.log('No test failure requiring debugging.'); return state
            state.retry_count += 1
            detail=(state.test_results.stderr or state.test_results.stdout or '\n'.join(state.test_results.failures_detail) or 'Unknown test failure').strip()
            state.log(f'Debug attempt {state.retry_count}/{state.max_retries}: {detail[-1200:]}')
            if self.llm and state.retry_count <= state.max_retries:
                prompt=("You are a repair agent. Return ONLY JSON with file_path, target_snippet, replacement_snippet. "
                        "Make the smallest safe fix. If you cannot determine a safe fix, return {}.\n"
                        f"Request: {state.user_request}\nFailure:\n{detail[-5000:]}\n"
                        f"Changed files:\n{[x.file_path for x in state.changed_files]}")
                try:
                    raw=self.llm.generate(prompt)
                    match=re.search(r'\{.*\}',raw,re.S)
                    suggestion=json.loads(match.group(0)) if match else {}
                    if suggestion.get('file_path') and suggestion.get('target_snippet') is not None and suggestion.get('replacement_snippet') is not None:
                        state.repair_suggestion=suggestion; state.log(f"Repair suggestion generated for {suggestion['file_path']}.")
                except Exception as exc: state.log(f'Repair generation unavailable: {type(exc).__name__}: {exc}')
            return state
        finally: tracer.end_span(span.span_id)
