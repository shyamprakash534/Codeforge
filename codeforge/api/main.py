"""FastAPI service for CodeForge."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator

app = FastAPI(title="CodeForge API", version="1.0.0")
_runs = 0
_successes = 0

class RunRequest(BaseModel):
    repo_path: str = "."
    request: str
    patch_suggestion: dict | None = None
    approved: bool = False


def _safe_repo_path(repo_path: str) -> str:
    root = os.path.realpath(os.getenv("CODEFORGE_WORKSPACE_ROOT", os.getcwd()))
    candidate = os.path.realpath(os.path.join(root, repo_path)) if not os.path.isabs(repo_path) else os.path.realpath(repo_path)
    try:
        inside = os.path.commonpath([root, candidate]) == root
    except ValueError:
        inside = False
    if not inside:
        raise PermissionError("repo_path must remain inside CODEFORGE_WORKSPACE_ROOT")
    if not os.path.isdir(candidate):
        raise FileNotFoundError(f"Repository path not found: {candidate}")
    return candidate


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>CodeForge</title>
<style>body{font-family:Inter,system-ui;margin:0;background:#0b1020;color:#eef2ff}main{max-width:900px;margin:40px auto;padding:24px}h1{font-size:40px;margin-bottom:8px}p{color:#aab4d0}textarea,input{width:100%;box-sizing:border-box;background:#151d33;color:#fff;border:1px solid #33405f;border-radius:10px;padding:14px;margin:8px 0 16px;font:inherit}textarea{min-height:150px}button{background:#6d7cff;color:white;border:0;border-radius:10px;padding:13px 22px;font-weight:700;font-size:16px;cursor:pointer}button:disabled{opacity:.6}pre{white-space:pre-wrap;overflow:auto;background:#070b15;border:1px solid #26314d;border-radius:10px;padding:16px;margin-top:20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:650px){.grid{grid-template-columns:1fr}main{margin:15px auto;padding:18px}}</style></head>
<body><main><h1>⚒ CodeForge</h1><p>Autonomous software factory — submit a coding task and inspect the workflow result.</p>
<label>Repository path</label><input id="repo" value="."><label>What should CodeForge do?</label><textarea id="request" placeholder="Example: Add a health-check test and improve the README."></textarea>
<button id="run">Run CodeForge</button><pre id="out" aria-live="polite">Ready. Submit a request to start.</pre></main>
<script>const btn=document.getElementById('run'),out=document.getElementById('out');btn.onclick=async()=>{const request=document.getElementById('request').value.trim();if(!request){out.textContent='Please enter a task.';return}btn.disabled=true;out.textContent='Running CodeForge...';try{const r=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({repo_path:document.getElementById('repo').value||'.',request})});const data=await r.json();out.textContent=JSON.stringify(data,null,2)}catch(e){out.textContent='Request failed: '+e.message}finally{btn.disabled=false}}</script></body></html>"""


@app.get("/health")
def health():
    return {"status": "ok", "service": "codeforge"}


@app.get("/metrics")
def metrics():
    return f"# HELP codeforge_runs_total Total workflow runs\n# TYPE codeforge_runs_total counter\ncodeforge_runs_total {_runs}\n# HELP codeforge_success_total Successful workflow runs\n# TYPE codeforge_success_total counter\ncodeforge_success_total {_successes}\n"


@app.post("/run")
def run(req: RunRequest):
    global _runs, _successes
    _runs += 1
    try:
        repo = _safe_repo_path(req.repo_path)
        state = CodeForgeOrchestrator(repo).run(req.request, req.patch_suggestion, req.approved)
        if state.phase.value == "DONE":
            _successes += 1
        return state.model_dump()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="CodeForge execution failed")
