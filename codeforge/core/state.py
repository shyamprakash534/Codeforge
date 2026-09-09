"""Typed State and Models for CodeForge Workflow."""
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import uuid
from pydantic import BaseModel, Field

class TaskPhase(str, Enum):
    INTAKE="INTAKE"; PLAN="PLAN"; RESEARCH="RESEARCH"; ARCHITECT="ARCHITECT"; IMPLEMENT="IMPLEMENT"; TEST="TEST"; DEBUG="DEBUG"; REVIEW="REVIEW"; SECURITY="SECURITY"; APPROVAL="APPROVAL"; PATCH_PR="PATCH_PR"; EVALUATE="EVALUATE"; DONE="DONE"; FAILED="FAILED"
class ApprovalStatus(str, Enum):
    PENDING="PENDING"; APPROVED="APPROVED"; REJECTED="REJECTED"
class Evidence(BaseModel):
    file_path:str; start_line:int; end_line:int; symbol:Optional[str]=None; content:str; relevance_score:float=0.0; doc_type:str="code"
class PlanStep(BaseModel):
    step_id:int; description:str; target_files:List[str]=Field(default_factory=list); acceptance_criteria:str; status:str="pending"
class TaskPlan(BaseModel):
    summary:str; acceptance_criteria:List[str]=Field(default_factory=list); steps:List[PlanStep]=Field(default_factory=list)
class FileChange(BaseModel):
    file_path:str; action:str="edit"; original_snippet:str=""; new_snippet:str=""; diff:str=""
class TestResult(BaseModel):
    total:int=0; passed:int=0; failed:int=0; errors:int=0; failures_detail:List[str]=Field(default_factory=list); duration_sec:float=0.0; stdout:str=""; stderr:str=""; exit_code:int=0
    @property
    def is_success(self)->bool: return self.exit_code==0 and self.failed==0 and self.errors==0
class ReviewFinding(BaseModel):
    category:str; severity:str; file_path:str; line_number:Optional[int]=None; comment:str; approved:bool=True
class SecurityFinding(BaseModel):
    risk_type:str; severity:str; file_path:str; line_number:Optional[int]=None; description:str; recommendation:str; passed:bool=True
class TaskState(BaseModel):
    task_id:str=Field(default_factory=lambda:str(uuid.uuid4())[:8]); repo_id:str="default_repo"; repo_path:str=""; user_request:str=""; phase:TaskPhase=TaskPhase.INTAKE
    plan:Optional[TaskPlan]=None; evidence:List[Evidence]=Field(default_factory=list); architecture_decision:Optional[str]=None
    changed_files:List[FileChange]=Field(default_factory=list); diff:str=""; test_results:Optional[TestResult]=None
    review_findings:List[ReviewFinding]=Field(default_factory=list); security_findings:List[SecurityFinding]=Field(default_factory=list)
    retry_count:int=0; max_retries:int=3; repair_suggestion:Optional[Dict[str,Any]]=None
    approval_status:ApprovalStatus=ApprovalStatus.PENDING; final_patch:Optional[str]=None; pr_metadata:Optional[Dict[str,Any]]=None
    logs:List[str]=Field(default_factory=list); trace_id:str=Field(default_factory=lambda:f"tr_{uuid.uuid4().hex[:12]}")
    created_at:float=Field(default_factory=time.time); updated_at:float=Field(default_factory=time.time)
    def log(self,message:str):
        timestamp=time.strftime("%H:%M:%S"); self.logs.append(f"[{timestamp}] [{self.phase.value}] {message}"); self.updated_at=time.time()
