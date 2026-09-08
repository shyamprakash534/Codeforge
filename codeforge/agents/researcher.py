"""Researcher Agent: discovers code evidence, symbols, tests, and dependencies."""
from codeforge.core.state import TaskState, TaskPhase
from codeforge.core.retrieval.hybrid_engine import HybridRetrievalEngine
from codeforge.ingestion.ast_parser import RepositoryScanner
from codeforge.observability.tracer import TraceCollector

class ResearcherAgent:
    def __init__(self, scanner: RepositoryScanner, retrieval: HybridRetrievalEngine):
        self.scanner = scanner
        self.retrieval = retrieval

    def run(self, state: TaskState, tracer: TraceCollector) -> TaskState:
        span = tracer.start_span("agent.researcher", span_type="agent", attributes={"query": state.user_request})
        try:
            state.phase = TaskPhase.RESEARCH
            state.log("Scanning repository and gathering code evidence via hybrid retrieval...")
            self.scanner.scan()
            self.retrieval.build_index()
            state.evidence = self.retrieval.search(state.user_request, top_k=5)
            state.log(f"Retrieved {len(state.evidence)} evidence chunks across {len(set(e.file_path for e in state.evidence))} files.")
            for ev in state.evidence:
                state.log(f" - Evidence: {ev.file_path}:{ev.start_line}-{ev.end_line} ({ev.symbol or 'module'}) score={ev.relevance_score}")
            return state
        finally:
            tracer.end_span(span.span_id)
