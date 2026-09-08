"""FastAPI service and web UI for CodeForge."""
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
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeForge — Autonomous Software Factory</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#080b14;color:#f4f7ff}main{max-width:980px;margin:0 auto;padding:56px 22px 70px}.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:30px}.eyebrow{display:inline-flex;padding:6px 10px;border:1px solid #26324d;border-radius:999px;color:#9eacd0;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.brand{font-size:48px;line-height:1;margin:16px 0 12px;letter-spacing:-.04em}.brand span{color:#8b9cff}.sub{max-width:650px;color:#a9b3ca;font-size:17px;line-height:1.6;margin:0}.links{display:flex;gap:10px;flex-wrap:wrap}.links a{color:#b9c5e8;text-decoration:none;border:1px solid #26324d;border-radius:10px;padding:9px 12px;font-size:13px}.panel{background:#101625;border:1px solid #26324d;border-radius:18px;padding:24px}.panel h2{margin:0 0 5px;font-size:20px}.hint{color:#8490aa;font-size:13px;margin:0 0 20px}.grid{display:grid;grid-template-columns:1fr 2fr;gap:18px}.field{display:flex;flex-direction:column}.field label{font-size:13px;font-weight:700;color:#cbd4ea;margin-bottom:8px}input,textarea{width:100%;border:1px solid #303c59;background:#090e1b;color:#f4f7ff;border-radius:11px;padding:13px 14px;font:inherit;outline:none}input:focus,textarea:focus{border-color:#7f8fff;box-shadow:0 0 0 3px #7f8fff22}textarea{min-height:150px;resize:vertical}.actions{display:flex;align-items:center;gap:12px;margin-top:18px}button{border:0;border-radius:11px;padding:13px 18px;background:#7f8fff;color:#080b14;font-weight:800;font-size:14px;cursor:pointer}button:hover{filter:brightness(1.08)}button:disabled{opacity:.55;cursor:wait}.status{color:#8f9bb7;font-size:13px}.output{margin-top:18px;background:#070a12;border:1px solid #202b43;border-radius:12px;min-height:170px;padding:16px;white-space:pre-wrap;overflow:auto;color:#dbe3f7;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}.flow{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:18px}.step{padding:10px 6px;text-align:center;border:1px solid #222d45;border-radius:10px;color:#8f9bb7;font-size:11px}.step b{display:block;color:#d8e0f5;font-size:12px;margin-bottom:4px}@media(max-width:720px){main{padding:32px 16px 50px}.hero{display:block}.brand{font-size:40px}.grid{grid-template-columns:1fr}.flow{grid-template-columns:repeat(3,1fr)}}
</style></head>
<body><main>
<section class="hero"><div><span class="eyebrow">Autonomous Software Factory</span><h1 class="brand">⚒ Code<span>Forge</span></h1><p class="sub">Turn a high-level software request into a controlled engineering workflow — from planning and architecture to testing, review and security.</p></div><nav class="links"><a href="/docs">API Docs</a><a href="/health">Health</a></nav></section>
<section class="panel"><h2>Run an engineering task</h2><p class="hint">Point CodeForge at a repository and describe the change in plain English.</p><div class="grid"><div class="field"><label for="repo">Repository path</label><input id="repo" value="." aria-label="Repository path"></div><div class="field"><label for="request">Task</label><textarea id="request" placeholder="Example: Add a health-check test and improve the README." aria-label="Task"></textarea></div></div><div class="actions"><button id="run" type="button">Run CodeForge</button><span class="status" id="status" aria-live="polite">Ready</span></div><pre class="output" id="out" aria-live="polite">Workflow output will appear here.</pre></section>
<div class="flow" aria-label="CodeForge workflow"><div class="step"><b>1</b>Plan</div><div class="step"><b>2</b>Research</div><div class="step"><b>3</b>Architect</div><div class="step"><b>4</b>Code</div><div class="step"><b>5</b>Test & Review</div><div class="step"><b>6</b>Secure & Approve</div></div>
</main><script>
const btn=document.getElementById('run'),out=document.getElementById('out'),status=document.getElementById('status');
btn.addEventListener('click',async()=>{const request=document.getElementById('request').value.trim(),repo=document.getElementById('repo').value.trim()||'.';if(!request){status.textContent='Enter a task first.';out.textContent='Please describe what you want CodeForge to do.';return}btn.disabled=true;status.textContent='Running workflow…';out.textContent='CodeForge is planning, researching, coding and testing your task.\n\nPlease wait…';try{const r=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({repo_path:repo,request})});const text=await r.text();let data;try{data=JSON.parse(text)}catch{data=text}if(!r.ok)throw new Error(typeof data==='string'?data:(data.detail||'Request failed'));out.textContent=JSON.stringify(data,null,2);status.textContent='Workflow completed';}catch(e){out.textContent='Error: '+e.message;status.textContent='Workflow failed';}finally{btn.disabled=false}});
</script></body></html>"""


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
