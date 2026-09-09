"""FastAPI service and web UI for CodeForge."""
import os
import re
import shutil
import subprocess
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from codeforge.agents.planner import PlannerAgent
from codeforge.agents.researcher import ResearcherAgent
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator
from codeforge.core.retrieval.hybrid_engine import HybridRetrievalEngine
from codeforge.core.state import TaskPhase, TaskState
from codeforge.ingestion.ast_parser import RepositoryScanner
from codeforge.observability.tracer import TraceCollector

app = FastAPI(title="CodeForge API", version="1.3.1")
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
    candidate = os.path.realpath(repo_path if os.path.isabs(repo_path) else os.path.join(root, repo_path))
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
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, target],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(target, ignore_errors=True)
        raise
    if result.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(result.stderr.strip() or "Git clone failed")
    return target


def _public_github_preview(repo: str, request: str) -> dict:
    """Analyze a public repository without executing repository code."""
    state = TaskState(repo_path=repo, user_request=request)
    tracer = TraceCollector()
    try:
        state = PlannerAgent().run(state, tracer)
        scanner = RepositoryScanner(repo)
        retrieval = HybridRetrievalEngine(scanner)
        state = ResearcherAgent(scanner, retrieval).run(state, tracer)
        state.phase = TaskPhase.DONE
        state.pr_metadata = {
            "preview": True,
            "execution": "analysis_only",
            "message": "Public GitHub preview completed. No repository code, tests, builds, or external commands were executed.",
        }
        state.log("Public GitHub preview completed successfully.")
        result = state.model_dump()
        result["mode"] = "PUBLIC_GITHUB_PREVIEW"
        result["result"] = "ANALYSIS_COMPLETE"
        result["note"] = "Full code changes, test execution, repair, and PR creation require a trusted local workspace."
        return result
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def _run_workflow(req: RunRequest) -> dict:
    if req.repo_url:
        repo = _clone_github(req.repo_url)
        return _public_github_preview(repo, req.request)
    repo = _safe_repo_path(req.repo_path)
    return CodeForgeOrchestrator(repo).run(req.request, req.patch_suggestion, req.approved).model_dump()


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeForge — Autonomous Software Factory</title>
<style>
body{margin:0;font-family:system-ui,sans-serif;background:#080b14;color:#f4f7ff}main{max-width:960px;margin:auto;padding:40px 20px}.panel{background:#101625;border:1px solid #26324d;border-radius:18px;padding:24px}h1{font-size:44px;margin:0 0 10px}h1 span{color:#8b9cff}.sub,.hint{color:#a9b3ca;line-height:1.5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input,textarea{width:100%;box-sizing:border-box;border:1px solid #303c59;background:#090e1b;color:#fff;border-radius:10px;padding:13px;font:inherit}textarea{min-height:150px;resize:vertical}.actions{display:flex;gap:12px;align-items:center;margin-top:16px}button{border:0;border-radius:10px;padding:13px 18px;background:#8b9cff;color:#080b14;font-weight:800}button:disabled{opacity:.55}.status{color:#9eacd0}.output{margin-top:18px;min-height:220px;padding:16px;background:#070a12;border:1px solid #202b43;border-radius:12px;white-space:pre-wrap;overflow:auto;font:13px/1.5 monospace}.success{border-color:#355d4b}.error{border-color:#6b3942}.flow{margin-top:16px;color:#9eacd0;font-size:13px}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body><main>
<h1>⚒ Code<span>Forge</span></h1>
<p class="sub">Autonomous software engineering workflow with safe public GitHub analysis.</p>
<section class="panel"><h2>Run an engineering task</h2>
<p class="hint">Public GitHub URLs use analysis-only mode. Local workspaces can run the full engineering workflow.</p>
<div class="grid"><div class="field"><label for="repo">GitHub repository URL or local path</label><input id="repo" placeholder="https://github.com/owner/repository or ."></div>
<div class="field"><label for="request">Task</label><textarea id="request" placeholder="Analyze this repository and explain how the health-check endpoint works."></textarea></div></div>
<div class="actions"><button id="run">Run CodeForge</button><span class="status" id="status">Ready</span></div>
<pre class="output" id="out">Workflow output will appear here.</pre></section>
<div class="flow">Plan → Research → Architect → Code → Test & Review → Secure & PR</div>
</main><script>
const btn=document.getElementById('run'),out=document.getElementById('out'),status=document.getElementById('status');
btn.onclick=async()=>{const raw=document.getElementById('repo').value.trim(),request=document.getElementById('request').value.trim();if(!raw||!request){status.textContent='Repository and task are required.';return}btn.disabled=true;status.textContent=raw.startsWith('https://github.com/')?'Analyzing public GitHub repository…':'Running local CodeForge workflow…';out.className='output';out.textContent='CodeForge started.\n\nValidating input…\nPreparing repository…\nRunning workflow…\n\nPlease wait for the result.';try{const body={request};if(raw.startsWith('https://github.com/'))body.repo_url=raw;else body.repo_path=raw;const response=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const text=await response.text();let data;try{data=JSON.parse(text)}catch{data={detail:text}}if(!response.ok)throw new Error(data.detail||'Request failed');out.className='output success';out.textContent=JSON.stringify(data,null,2);status.textContent=data.result==='ANALYSIS_COMPLETE'?'✓ Analysis complete':'✓ Workflow completed'}catch(error){out.className='output error';out.textContent='Error: '+error.message;status.textContent='✗ Workflow failed'}finally{btn.disabled=false}};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "codeforge",
        "github_repo_input": True,
        "public_github_mode": "analysis_only",
    }


@app.get("/metrics")
def metrics():
    return (
        "# HELP codeforge_runs_total Total workflow runs\n"
        "# TYPE codeforge_runs_total counter\n"
        f"codeforge_runs_total {_runs}\n"
        "# HELP codeforge_success_total Successful workflow runs\n"
        f"codeforge_success_total {_successes}\n"
    )


@app.post("/run")
def run(req: RunRequest):
    global _runs, _successes
    _runs += 1
    try:
        result = _run_workflow(req)
        if result.get("result") == "ANALYSIS_COMPLETE" or result.get("phase") == "DONE":
            _successes += 1
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Repository clone timed out after 90 seconds")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CodeForge execution failed: {type(exc).__name__}")
