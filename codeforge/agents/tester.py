"""Tester agent with safe subprocess execution."""
from codeforge.core.state import TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector
from codeforge.tools.test_tool import TestRunner

class TesterAgent:
    def __init__(self, repo_path: str):
        self.runner = TestRunner(repo_path)

    def run(self, state: TaskState, tracer: TraceCollector) -> TaskState:
        span = tracer.start_span("agent.tester", span_type="agent")
        state.phase = TaskPhase.TEST
        state.test_results = self.runner.run()
        state.log(f"Tests completed: passed={state.test_results.passed}, failed={state.test_results.failed}, errors={state.test_results.errors}.")
        tracer.end_span(span.span_id)
        return state
