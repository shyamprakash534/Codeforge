"""FastAPI service for CodeForge."""
import os
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc: raise RuntimeError("Install the 'api' extra to use the HTTP API") from exc
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator
app=FastAPI(title='CodeForge API',version='1.0.0')
_runs=0; _successes=0
class RunRequest(BaseModel):
    repo_path:str='.'; request:str; patch_suggestion:dict|None=None; approved:bool=False

def _safe_repo_path(repo_path:str)->str:
    root=os.path.realpath(os.getenv('CODEFORGE_WORKSPACE_ROOT', os.getcwd()))
    candidate=os.path.realpath(os.path.join(root, repo_path)) if not os.path.isabs(repo_path) else os.path.realpath(repo_path)
    try: inside=os.path.commonpath([root,candidate])==root
    except ValueError: inside=False
    if not inside: raise PermissionError('repo_path must remain inside CODEFORGE_WORKSPACE_ROOT')
    if not os.path.isdir(candidate): raise FileNotFoundError(f'Repository path not found: {candidate}')
    return candidate

@app.get('/health')
def health(): return {'status':'ok','service':'codeforge'}
@app.get('/metrics')
def metrics():
    return f'# HELP codeforge_runs_total Total workflow runs\n# TYPE codeforge_runs_total counter\ncodeforge_runs_total {_runs}\n# HELP codeforge_success_total Successful workflow runs\n# TYPE codeforge_success_total counter\ncodeforge_success_total {_successes}\n'
@app.post('/run')
def run(req:RunRequest):
    global _runs,_successes
    _runs+=1
    try:
        repo=_safe_repo_path(req.repo_path)
        state=CodeForgeOrchestrator(repo).run(req.request,req.patch_suggestion,req.approved)
        if state.phase.value=='DONE': _successes+=1
        return state.model_dump()
    except PermissionError as exc: raise HTTPException(status_code=403,detail=str(exc))
    except FileNotFoundError as exc: raise HTTPException(status_code=400,detail=str(exc))
    except Exception: raise HTTPException(status_code=500,detail='CodeForge execution failed')
