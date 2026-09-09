"""FastAPI service and web UI for CodeForge."""
import os
import re
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator

app = FastAPI(title="CodeForge API", version="1.2.1")
_runs = 0
_successes = 0

class RunRequest(BaseModel):
    repo_path: str = "."
    repo_url: str | None = None
    request: str
    patch_suggestion: dict | None = None
    approved: bool = False


def _workspace_root() -> str:
    root = os.path.realpath(os.getenv("CODEFORGE_WORKSPACE_ROOT", os.getcwd()))
    os.makedirs(root, exist_ok=True)
    return root


def _safe_repo_path(repo_path: str) -> str:
    root = _workspace_root()
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


def _clone_github(repo_url: str) -> str:
    url = repo_url.strip()
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?", url):
        raise ValueError("Only public HTTPS GitHub repository URLs are supported.")
    name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    target = tempfile.mkdtemp(prefix=f"{name}-", dir=_workspace_root())
    result = subprocess.run(["git", "clone", "--depth", "1", url, target], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(result.stderr.strip() or "Git clone failed")
    return target


def _run_workflow(req: RunRequest):
    if req.repo_url:
        repo = _clone_github(req.repo_url)
    else:
        repo = _safe_repo_path(req.repo_path)
    return CodeForgeOrchestrator(repo).run(req.request, req.patch_suggestion, req.approved)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeForge — Autonomous Software Factory</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:#080b14;color:#f4f7ff}main{max-width:1000px;margin:auto;padding:52px 22px 70px}.hero{display:flex;justify-content:space-between;gap:24px;margin-bottom:28px}.eyebrow{padding:6px 10px;border:1px solid #26324d;border-radius:999px;color:#9eacd0;font-size:12px;font-weight:700;text-transform:uppercase}.brand{font-size:48px;margin:16px 0 12px}.brand span{color:#8b9cff}.sub{max-width:700px;color:#a9b3ca;font-size:17px;line-height:1.6}.links{display:flex;gap:10px}.links a{color:#b9c5e8;text-decoration:none;border:1px solid #26324d;border-radius:10px;padding:9px 12px;font-size:13px}.panel{background:#101625;border:1px solid #26324d;border-radius:18px;padding:24px}.hint{color:#8490aa;font-size:13px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field label{display:block;font-size:13px;font-weight:700;color:#cbd4ea;margin-bottom:8px}input,textarea{width:100%;border:1px solid #303c59;background:#090e1b;color:#f4f7ff;border-radius:11px;padding:13px 14px;font:inherit}textarea{min-height:150px;resize:vertical}.actions{display:flex;align-items:center;gap:12px;margin-top:18px}button{border:0;border-radius:11px;padding:13px 18px;background:#7f8fff;color:#080b14;font-weight:800;cursor:pointer}.status{color:#8f9bb7;font-size:13px}.output{margin-top:18px;background:#070a12;border:1px solid #202b43;border-radius:12px;min-height:190px;padding:16px;white-space:pre-wrap;overflow:auto;color:#dbe3f7;font:13px/1.6 ui-monospace,monospace}.flow{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:18px}.step{padding:10px 6px;text-align:center;border:1px solid #222d45;border-radius:10px;color:#8f9bb7;font-size:11px}.step b{display:block;color:#d8e0f5;margin-bottom:4px}@media(max-width:720px){.hero{display:block}.grid{grid-template-columns:1fr}.flow{grid-template-columns:repeat(3,1fr)}}
</style></head><body><main>
<section class="hero"><div><span class="eyebrow">Autonomous Software Factory</span><h1 class="brand">⚒ Code<span>Forge</span></h1><p class="sub">Give CodeForge a public GitHub repository or a local workspace, then describe the engineering task in plain English.</p></div><nav class="links"><a href="/docs">API Docs</a><a href="/health">Health</a></nav></section>
<section class="panel"><h2>Run an engineering task</h2><p class="hint">For the live demo, paste a public GitHub URL. For local development, use a repository path inside the configured workspace.</p><div class="grid"><div class="field"><label for="repo">GitHub repository URL or local path</label><input id="repo" placeholder="https://github.com/owner/repository or ." aria-label="Repository"></div><div class="field"><label for="request">Task</label><textarea id="request" placeholder="Example: Add a health-check test and improve the README." aria-label="Task"></textarea></div></div><div class="actions"><button id="run" type="button">Run CodeForge</button><span class="status" id="status">Ready</span></div><pre class="output" id="out">Workflow output will appear here.</pre></section>
<div class="flow"><div class="step"><b>1</b>Plan</div><div class="step"><b>2</b>Research</div><div class="step"><b>3</b>Architect</div><div class="step"><b>4</b>Code</div><div class="step"><b>5</b>Test & Review</div><div class="step"><b>6</b>Secure & PR</div></div>
</main><script>
const btn=document.getElementById('run'),out=document.getElementById('out'),status=document.getElementById('status');
btn.onclick=async()=>{const raw=document.getElementById('repo').value.trim(),request=document.getElementById('request').value.trim();if(!raw||!request){status.textContent='Repository and task are required.';return}btn.disabled=true;status.textContent='Preparing repository and running workflow…';out.textContent='CodeForge is preparing the repository and running the engineering pipeline.\n\nPlease wait…';const body={request};if(raw.startsWith('https://github.com/'))body.repo_url=raw;else body.repo_path=raw;try{const r=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const text=await r.text();let data;try{data=JSON.parse(text)}catch{data=text}if(!r.ok)throw new Error(typeof data==='string'?data:(data.detail||'Request failed'));out.textContent=JSON.stringify(data,null,2);status.textContent=data.phase==='DONE'?'Workflow completed':'Workflow finished with status: '+data.phase}catch(e){out.textContent='Error: '+e.message;status.textContent='Workflow failed'}finally{btn.disabled=false}};
</script></body></html>"""

@app.get("/health")
def health(): return {"status":"ok","service":"codeforge","github_repo_input":True}

@app.get("/metrics")
def metrics(): return f"# HELP codeforge_runs_total Total workflow runs\n# TYPE codeforge_runs_total counter\ncodeforge_runs_total {_runs}\n# HELP codeforge_success_total Successful workflow runs\ncodeforge_success_total {_successes}\n"

@app.post("/run")
def run(req: RunRequest):
    global _runs, _successes
    _runs += 1
    try:
        state = _run_workflow(req)
        if state.phase.value == "DONE": _successes += 1
        return state.model_dump()
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc))
    except (FileNotFoundError, ValueError) as exc: raise HTTPException(status_code=400, detail=str(exc))
    except subprocess.TimeoutExpired: raise HTTPException(status_code=504, detail="Repository clone timed out")
    except RuntimeError as exc: raise HTTPException(status_code=502, detail=str(exc))
    except Exception: raise HTTPException(status_code=500, detail="CodeForge execution failed")
