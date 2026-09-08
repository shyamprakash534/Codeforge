"""Deterministic code review agent for correctness and maintainability checks."""
import ast
import os
from codeforge.core.state import ReviewFinding, TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector

class ReviewerAgent:
    def __init__(self, repo_path: str): self.repo_path = os.path.abspath(repo_path)
    def run(self, state: TaskState, tracer: TraceCollector) -> TaskState:
        span = tracer.start_span("agent.reviewer", span_type="agent")
        state.phase = TaskPhase.REVIEW
        findings = []
        for change in state.changed_files:
            path = os.path.join(self.repo_path, change.file_path)
            if not os.path.isfile(path):
                findings.append(ReviewFinding(category="correctness", severity="high", file_path=change.file_path, comment="Changed file does not exist." , approved=False)); continue
            if path.endswith('.py'):
                try:
                    ast.parse(open(path, encoding='utf-8').read())
                except SyntaxError as exc:
                    findings.append(ReviewFinding(category="correctness", severity="critical", file_path=change.file_path, line_number=exc.lineno, comment=f"Python syntax error: {exc.msg}", approved=False))
        state.review_findings = findings
        state.log(f"Review completed with {len(findings)} blocking findings.")
        tracer.end_span(span.span_id)
        return state
