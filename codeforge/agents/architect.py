"""Architecture agent that converts retrieved evidence into a bounded design."""
from codeforge.core.state import TaskState, TaskPhase
from codeforge.observability.tracer import TraceCollector

class ArchitectureAgent:
    def run(self, state: TaskState, tracer: TraceCollector) -> TaskState:
        span = tracer.start_span("agent.architect", span_type="agent")
        state.phase = TaskPhase.ARCHITECT
        files = ", ".join(e.file_path for e in state.evidence[:8]) or "repository root"
        state.architecture_decision = (
            "Use existing project conventions and make the smallest targeted change. "
            f"Primary evidence: {files}. Keep interfaces typed, changes testable, and execution confined to the workspace."
        )
        state.log("Produced architecture decision from repository evidence.")
        tracer.end_span(span.span_id)
        return state
