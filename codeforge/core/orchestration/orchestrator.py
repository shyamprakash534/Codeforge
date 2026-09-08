"""End-to-end CodeForge workflow orchestrator.

The default engine is dependency-light and deterministic; optional LLM/UI integrations
can plug into the same state machine without bypassing security or approval gates.
"""
from codeforge.agents.planner import PlannerAgent
from codeforge.agents.researcher import ResearcherAgent
from codeforge.agents.architect import ArchitectureAgent
from codeforge.agents.coder import CoderAgent
from codeforge.agents.tester import TesterAgent
from codeforge.agents.debugger import DebuggerAgent
from codeforge.agents.reviewer import ReviewerAgent
from codeforge.approval.gate import ApprovalGate
from codeforge.core.security.security_policy import SecurityPolicyEngine
from codeforge.core.state import TaskState, TaskPhase
from codeforge.core.retrieval.hybrid_engine import HybridRetrievalEngine
from codeforge.ingestion.ast_parser import RepositoryScanner
from codeforge.observability.tracer import TraceCollector

class CodeForgeOrchestrator:
    def __init__(self, repo_path:str):
        self.repo_path=repo_path; self.scanner=RepositoryScanner(repo_path)
        self.retrieval=HybridRetrievalEngine(self.scanner)
        self.planner=PlannerAgent(); self.researcher=ResearcherAgent(self.scanner,self.retrieval)
        self.architect=ArchitectureAgent(); self.coder=CoderAgent(repo_path); self.tester=TesterAgent(repo_path)
        self.debugger=DebuggerAgent(); self.reviewer=ReviewerAgent(repo_path); self.approval=ApprovalGate()
    def run(self,user_request:str,patch_suggestion:dict|None=None,approved:bool=False)->TaskState:
        state=TaskState(repo_path=self.repo_path,user_request=user_request); tracer=TraceCollector()
        try:
            state=self.planner.run(state,tracer); state=self.researcher.run(state,tracer); state=self.architect.run(state,tracer)
            state=self.coder.run(state,tracer,patch_suggestion)
            state=self.tester.run(state,tracer)
            if state.test_results and not state.test_results.is_success: state=self.debugger.run(state,tracer)
            state=self.reviewer.run(state,tracer)
            state.security_findings=SecurityPolicyEngine.scan_diff(state.diff)
            state.phase=TaskPhase.SECURITY; state.log(f'Security scan found {len(state.security_findings)} findings.')
            state=self.approval.evaluate(state,approved=approved)
            blocking=(state.test_results and not state.test_results.is_success) or any(not f.approved for f in state.review_findings) or any(not f.passed for f in state.security_findings)
            state.phase=TaskPhase.DONE if state.approval_status.value=='APPROVED' and not blocking else TaskPhase.FAILED
            state.log('Workflow completed.' if state.phase==TaskPhase.DONE else 'Workflow stopped pending fixes or approval.')
            return state
        except Exception as exc:
            state.phase=TaskPhase.FAILED; state.log(f'Workflow error: {type(exc).__name__}: {exc}'); return state
