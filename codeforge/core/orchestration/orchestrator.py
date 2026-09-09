"""CodeForge orchestration: agents, bounded repair, security, approval and PR lifecycle."""
import os, re
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
from codeforge.tools.git_tool import GitTool
from codeforge.tools.github_tool import GitHubTool
from codeforge.llm.ollama import OllamaClient

class CodeForgeOrchestrator:
    def __init__(self,repo_path:str):
        self.repo_path=repo_path; self.scanner=RepositoryScanner(repo_path); self.retrieval=HybridRetrievalEngine(self.scanner)
        self.planner=PlannerAgent(); self.researcher=ResearcherAgent(self.scanner,self.retrieval); self.architect=ArchitectureAgent(); self.coder=CoderAgent(repo_path); self.tester=TesterAgent(repo_path); self.approval=ApprovalGate(); self.git=GitTool(repo_path)
        self.debugger=DebuggerAgent(repo_path, OllamaClient(base_url=os.getenv('OLLAMA_BASE_URL','http://localhost:11434'),model=os.getenv('OLLAMA_MODEL','qwen2.5-coder:7b')) if os.getenv('CODEFORGE_ENABLE_OLLAMA_REPAIR','0')=='1' else None)
        self.reviewer=ReviewerAgent(repo_path); self._tracer=None; self._patch_suggestion=None; self._approved=False; self._branch=None
    def _run_agent(self,agent,state,*args): return agent.run(state,self._tracer,*args)
    def _plan(self,s): return self._run_agent(self.planner,s)
    def _research(self,s): return self._run_agent(self.researcher,s)
    def _architect(self,s): return self._run_agent(self.architect,s)
    def _implement(self,s): return self._run_agent(self.coder,s,self._patch_suggestion or s.repair_suggestion)
    def _test(self,s): return self._run_agent(self.tester,s)
    def _debug(self,s): return self._run_agent(self.debugger,s)
    def _repair(self,s):
        if s.repair_suggestion:
            s=self._run_agent(self.coder,s,s.repair_suggestion); s.repair_suggestion=None
        return s
    def _review(self,s): return self._run_agent(self.reviewer,s)
    def _security(self,s):
        s.phase=TaskPhase.SECURITY; s.security_findings=SecurityPolicyEngine.scan_diff(s.diff); s.log(f'Security scan found {len(s.security_findings)} findings.'); return s
    def _approval(self,s): return self.approval.evaluate(s,approved=self._approved)
    def _blocking(self,s): return bool((s.test_results and not s.test_results.is_success) or any(not f.approved for f in s.review_findings) or any(not f.passed for f in s.security_findings))
    def _prepare_branch(self,s):
        try:
            if self.git.status()['ok']:
                name=f'codeforge/{s.task_id}'
                result=self.git.branch(name)
                if result['ok']: self._branch=name; s.log(f'Created isolated Git branch {name}.')
                else: s.log(f'Git branch creation skipped: {result.get("stderr",result.get("error","unknown"))}')
        except Exception as exc: s.log(f'Git integration unavailable: {type(exc).__name__}: {exc}')
        return s
    def _patch_pr(self,s):
        s.phase=TaskPhase.PATCH_PR
        if not self._branch or not s.changed_files:
            s.pr_metadata={'skipped':True,'reason':'No isolated branch or file changes.'}; s.log('PR stage skipped because there are no changes.'); return s
        commit=self.git.commit(f'CodeForge: {s.user_request[:72]}')
        if not commit['ok']:
            s.pr_metadata={'ok':False,'stage':'commit','error':commit['stderr']}; s.log('Git commit failed.'); return s
        push=self.git.push(self._branch)
        if not push['ok']:
            s.pr_metadata={'ok':False,'stage':'push','error':push['stderr']}; s.log('Git push failed; PR not created.'); return s
        remote=self.git.remote_url()['stdout'].strip(); m=re.search(r'github.com[/:]([^/]+)/([^/.]+?)(?:\.git)?$',remote)
        if not m: s.pr_metadata={'ok':False,'stage':'remote','error':'Origin is not a GitHub repository.'}; return s
        pr=GitHubTool().create_pull_request(m.group(1),m.group(2),self._branch,'main',f'CodeForge: {s.user_request[:72]}',f'Automated CodeForge change.\n\nTask: {s.user_request}\nTests: {s.test_results.passed if s.test_results else 0} passed.')
        s.pr_metadata=pr; s.log('Pull request created.' if pr.get('ok') else f'Pull request creation failed: {pr.get("error")}'); return s
    def _evaluate(self,s):
        s.phase=TaskPhase.EVALUATE
        pr_failed=bool(s.pr_metadata and s.pr_metadata.get('ok') is False)
        s.phase=TaskPhase.DONE if s.approval_status.value=='APPROVED' and not self._blocking(s) and not pr_failed else TaskPhase.FAILED
        s.log('Workflow completed.' if s.phase==TaskPhase.DONE else 'Workflow stopped pending fixes, approval, or PR delivery.'); return s
    def run(self,user_request:str,patch_suggestion:dict|None=None,approved:bool=False)->TaskState:
        state=TaskState(repo_path=self.repo_path,user_request=user_request); self._tracer=TraceCollector(); self._patch_suggestion=patch_suggestion; self._approved=approved
        try:
            state=self._prepare_branch(state)
            use_lg=os.getenv('CODEFORGE_USE_LANGGRAPH','0')=='1'
            if use_lg:
                from codeforge.core.orchestration.langgraph_workflow import LangGraphWorkflow
                state=LangGraphWorkflow(self).invoke(state)
            else:
                state=self._plan(state); state=self._research(state); state=self._architect(state); state=self._implement(state); state=self._test(state)
                while state.test_results and not state.test_results.is_success and state.retry_count<state.max_retries:
                    state=self._debug(state)
                    if not state.repair_suggestion: break
                    state=self._repair(state); state=self._test(state)
                state=self._review(state); state=self._security(state); state=self._approval(state)
                if state.approval_status.value=='APPROVED' and not self._blocking(state): state=self._patch_pr(state)
                state=self._evaluate(state)
            return state
        except Exception as exc:
            state.phase=TaskPhase.FAILED; state.log(f'Workflow error: {type(exc).__name__}: {exc}'); return state
