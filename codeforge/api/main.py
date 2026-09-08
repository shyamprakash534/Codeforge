"""FastAPI service for CodeForge. Install the optional 'api' extra to run it."""
from dataclasses import asdict
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc:
    raise RuntimeError("Install CodeForge with the 'api' extra to use the HTTP API") from exc
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator

app=FastAPI(title='CodeForge API',version='1.0.0')
class RunRequest(BaseModel):
    repo_path:str='.'; request:str; patch_suggestion:dict|None=None; approved:bool=False
@app.get('/health')
def health(): return {'status':'ok','service':'codeforge'}
@app.post('/run')
def run(req:RunRequest):
    try:
        state=CodeForgeOrchestrator(req.repo_path).run(req.request,req.patch_suggestion,req.approved)
        return state.model_dump()
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))
