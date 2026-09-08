"""Lightweight evaluation metrics and run reports."""
from dataclasses import dataclass, asdict
from typing import Any
@dataclass
class EvaluationReport:
    task_success: bool
    tests_passed: int
    tests_failed: int
    security_findings: int
    review_findings: int
    retry_count: int
    def to_dict(self)->dict[str,Any]: return asdict(self)
class Evaluator:
    def evaluate(self,state):
        tr=state.test_results
        return EvaluationReport(bool(tr and tr.is_success and not [f for f in state.security_findings if not f.passed]), tr.passed if tr else 0, tr.failed if tr else 0, len(state.security_findings), len(state.review_findings), state.retry_count)
