"""FastAPI service for CodeForge."""
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc: raise RuntimeError("Install the 'api' extra to use the HTTP API") from exc
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator
app=FastAPI(title='CodeForge API',version='1.0.0')
_runs=0; _successes=0
class RunRequest(BaseModel):
    repo_path:str='.'; request:str; patch_suggestion:dict|None=None; approved:bool=False
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
        state=CodeForgeOrchestrator(req.repo_path).run(req.request,req.patch_suggestion,req.approved)
        if state.phase.value=='DONE': _successes+=1
        return state.model_dump()
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))
