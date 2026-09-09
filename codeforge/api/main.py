"""FastAPI service and web UI for CodeForge."""
import html
import json
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

app = FastAPI(title="CodeForge API", version="1.4.1")
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
        result = subprocess.run(["git", "clone", "--depth", "1", url, target], capture_output=True, text=True, timeout=90)
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
        state.pr_metadata = {"preview": True, "execution": "analysis_only", "message": "Public GitHub preview completed. No repository code, tests, builds, or external commands were executed."}
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

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CodeForge — Autonomous Software Factory</title><style>
body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#080b14;color:#f4f7ff}main{max-width:960px;margin:auto;padding:40px 20px}.panel{background:#101625;border:1px solid #26324d;border-radius:18px;padding:24px}h1{font-size:44px;margin:0 0 10px}h1 span{color:#8b9cff}.sub,.hint{color:#a9b3ca;line-height:1.5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input,textarea{width:100%;box-sizing:border-box;border:1px solid #303c59;background:#090e1b;color:#fff;border-radius:10px;padding:13px;font:inherit}textarea{min-height:150px;resize:vertical}.actions{display:flex;gap:12px;align-items:center;margin-top:16px}button{border:0;border-radius:10px;padding:13px 18px;background:#8b9cff;color:#080b14;font-weight:800;cursor:pointer}.status{color:#9eacd0}.output{margin-top:18px;min-height:160px;padding:16px;background:#070a12;border:1px solid #202b43;border-radius:12px;white-space:pre-wrap;overflow:auto;font:13px/1.5 monospace}.flow{margin-top:16px;color:#9eacd0;font-size:13px}@media(max-width:700px){.grid{grid-template-columns:1fr}h1{font-size:36px}}
</style></head><body><main><h1>⚒ Code<span>Forge</span></h1><p class="sub">Autonomous software engineering workflow with safe public GitHub analysis.</p><section class="panel"><h2>Run an engineering task</h2><p class="hint">Public GitHub URLs use analysis-only mode. No repository code is executed on the public demo path.</p><form method="get" action="/run-ui"><div class="grid"><div class="field"><label for="repo">GitHub repository URL or local path</label><input id="repo" name="repo_url" required placeholder="https://github.com/owner/repository"></div><div class="field"><label for="request">Task</label><textarea id="request" name="request" required placeholder="Analyze this repository and explain how the health-check endpoint works."></textarea></div></div><div class="actions"><button type="submit">Run CodeForge</button><span class="status">Ready — submit to start</span></div></form><pre class="output">Enter a public GitHub URL and task, then press Run CodeForge.</pre></section><div class="flow">Plan → Research → Analysis Complete</div></main></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {"status":"ok","service":"codeforge","github_repo_input":True,"public_github_mode":"analysis_only"}

@app.get("/metrics")
def metrics():
    return "# HELP codeforge_runs_total Total workflow runs\n# TYPE codeforge_runs_total counter\n" + f"codeforge_runs_total {_runs}\n" + "# HELP codeforge_success_total Successful workflow runs\n" + f"codeforge_success_total {_successes}\n"

def _esc(value) -> str:
    return html.escape(str(value))

def _result_page(result: dict) -> str:
    plan = result.get("plan") or {}
    summary = _esc(plan.get("summary") or result.get("user_request") or "Analysis completed.")
    task_id = _esc(result.get("task_id", "—"))
    phase = _esc(result.get("phase", "—"))
    mode = _esc(result.get("mode", "FULL_WORKFLOW"))
    request = _esc(result.get("user_request", "—"))
    repo_path = _esc(result.get("repo_path", "—"))
    evidence = result.get("evidence") or []
    logs = result.get("logs") or []
    steps = plan.get("steps") or []
    cards = []
    for item in evidence[:8]:
        path = _esc(item.get("file_path", "unknown"))
        start = _esc(item.get("start_line", "?"))
        end = _esc(item.get("end_line", "?"))
        symbol = item.get("symbol")
        content = _esc(item.get("content", ""))
        symbol_html = "<div class='symbol'>" + _esc(symbol) + "</div>" if symbol else ""
        score = item.get("relevance_score", 0)
        cards.append("<div class='evidence'><div class='ev-head'><strong>" + path + "</strong><span>Lines " + start + "–" + end + "</span></div>" + symbol_html + "<pre>" + content + "</pre><div class='score'>Relevance " + f"{float(score):.2f}" + "</div></div>")
    evidence_html = "".join(cards) or "<div class='empty'>No evidence snippets were returned.</div>"
    step_html = "".join("<div class='step'><span class='check'>✓</span><div><strong>Step " + _esc(s.get("step_id", "")) + "</strong><div>" + _esc(s.get("description", "")) + "</div></div></div>" for s in steps)
    logs_text = "\n".join(str(x) for x in logs)
    raw = html.escape(json.dumps(result, indent=2, ensure_ascii=False))
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CodeForge Result</title><style>
body{margin:0;background:#080b14;color:#f4f7ff;font-family:system-ui,-apple-system,sans-serif}main{max-width:1050px;margin:auto;padding:28px 18px 60px}a{color:#aebaff}.top{display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap}.badge{padding:8px 12px;border:1px solid #31553d;border-radius:999px;background:#102117;color:#9ee6ad;font-weight:800;font-size:13px}h1{font-size:42px;margin:14px 0 6px}.muted{color:#9eabc5}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}.card,.section{background:#101625;border:1px solid #26324d;border-radius:16px;padding:18px}.label{font-size:12px;color:#8794b2;text-transform:uppercase;letter-spacing:.08em}.value{margin-top:7px;font-weight:750;word-break:break-word}.section{margin-top:16px}.section h2{margin:0 0 14px;font-size:20px}.summary{font-size:18px;line-height:1.55}.step{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #202b43}.step:last-child{border-bottom:0}.check{color:#8ee49f;font-weight:900}.evidence{margin:12px 0;padding:14px;border:1px solid #26324d;border-radius:12px;background:#0a0f1c}.ev-head{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}.ev-head span,.score{color:#8996b2;font-size:12px}.symbol{margin-top:6px;color:#aebaff;font-size:13px}.evidence pre,.logs,details pre{white-space:pre-wrap;overflow:auto}.evidence pre{margin:10px 0 0;color:#dbe3f7;font:13px/1.5 ui-monospace,SFMono-Regular,monospace}.logs{background:#070a12;border-radius:10px;padding:14px;color:#aeb9cf;font:12px/1.6 ui-monospace,SFMono-Regular,monospace}.empty{color:#8996b2}.raw{margin-top:16px}summary{cursor:pointer;font-weight:750}details pre{margin-top:12px;background:#070a12;border:1px solid #202b43;border-radius:10px;padding:14px;font:12px/1.5 ui-monospace,SFMono-Regular,monospace}@media(max-width:700px){.grid{grid-template-columns:1fr}h1{font-size:34px}}
</style></head><body><main><div class='top'><a href='/'>← Back to CodeForge</a><span class='badge'>✓ ANALYSIS COMPLETE</span></div><h1>CodeForge Result</h1><p class='muted'>Repository analysis finished successfully.</p><div class='grid'><div class='card'><div class='label'>Task ID</div><div class='value'>""" + task_id + """</div></div><div class='card'><div class='label'>Phase</div><div class='value'>""" + phase + """</div></div><div class='card'><div class='label'>Mode</div><div class='value'>""" + mode + """</div></div></div><div class='section'><div class='label'>Repository</div><div class='value'>""" + repo_path + """</div><div class='label' style='margin-top:14px'>Request</div><div class='value'>""" + request + """</div></div><div class='section'><h2>🧠 Analysis Summary</h2><div class='summary'>""" + summary + """</div></div><div class='section'><h2>🔄 Workflow</h2>""" + step_html + """</div><div class='section'><h2>🔎 Repository Evidence</h2>""" + evidence_html + """</div><div class='section'><h2>📋 Execution Log</h2><div class='logs'>""" + _esc(logs_text) + """</div></div><details class='section raw'><summary>🧾 View Raw JSON</summary><pre>""" + raw + """</pre></details></main></body></html>"""

@app.get("/run-ui", response_class=HTMLResponse)
def run_ui(repo_url: str = "", request: str = ""):
    global _runs, _successes
    if not repo_url.strip() or not request.strip():
        return HTMLResponse("<h2>Repository URL and task are required.</h2><p><a href='/'>Back to CodeForge</a></p>", status_code=400)
    _runs += 1
    try:
        result = _run_workflow(RunRequest(repo_url=repo_url, request=request))
        _successes += 1
        return _result_page(result)
    except subprocess.TimeoutExpired:
        return HTMLResponse("<h2>Repository clone timed out after 90 seconds.</h2><p><a href='/'>Back to CodeForge</a></p>", status_code=504)
    except (PermissionError, FileNotFoundError, ValueError, RuntimeError) as exc:
        return HTMLResponse("<h2>CodeForge failed</h2><pre>" + _esc(exc) + "</pre><p><a href='/'>Back to CodeForge</a></p>", status_code=502)
    except Exception as exc:
        return HTMLResponse("<h2>CodeForge execution failed</h2><pre>" + _esc(type(exc).__name__) + "</pre><p><a href='/'>Back to CodeForge</a></p>", status_code=500)

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
