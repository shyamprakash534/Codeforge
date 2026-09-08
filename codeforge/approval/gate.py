"""Human-in-the-loop approval gate for sensitive changes."""
from dataclasses import dataclass
from codeforge.core.state import ApprovalStatus, TaskPhase, TaskState
@dataclass
class ApprovalGate:
    sensitive_paths: tuple[str,...]=('secrets/','.env','credentials','migration')
    def requires_approval(self,state:TaskState)->bool:
        if any(any(token in c.file_path.lower() for token in self.sensitive_paths) for c in state.changed_files): return True
        return any(f.severity.lower() in {'critical','high'} for f in state.security_findings)
    def evaluate(self,state:TaskState,approved:bool=False)->TaskState:
        state.phase=TaskPhase.APPROVAL
        if self.requires_approval(state): state.approval_status=ApprovalStatus.APPROVED if approved else ApprovalStatus.PENDING
        else: state.approval_status=ApprovalStatus.APPROVED
        state.log(f'Approval status: {state.approval_status.value}.'); return state
