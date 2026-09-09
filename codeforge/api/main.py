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

app = FastAPI(title="CodeForge API", version="1.5.0")
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
body{margin:0;font-family:system-ui,sans-serif;background:#080b14;color:#f4f7ff}main{max-width:960px;margin:auto;padding:40px 20px}.panel{background:#101625;border:1px solid #26324d;border-radius:18px;padding:24px}h1{font-size:44px;margin:0 0 10px}h1 span{color:#8b9cff}.sub,.hint{color:#a9b3ca;line-height:1.5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}input,textarea{width:100%;box-sizing:border-box;border:1px solid #303c59;background:#090e1b;color:#fff;border-radius:10px;padding:13px;font:inherit}textarea{min-height:150px;resize:vertical}.actions{display:flex;gap:12px;align-items:center;margin-top:16px}button{border:0;border-radius:10px;padding:13px 18px;background:#8b9cff;color:#080b14;font-weight:800;cursor:pointer}.status{color:#9eacd0}.output{margin-top:18px;min-height:220px;padding:16px;background:#070a12;border:1px solid #202b43;border-radius:12px;white-space:pre-wrap;overflow:auto;font:13px/1.5 monospace}.flow{margin-top:16px;color:#9eacd0;font-size:13px}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body><main>
<h1>⚒ Code<span>Forge</span></h1>
<p class="sub">Autonomous software engineering workflow with safe public GitHub analysis.</p>
<section class="panel"><h2>Run an engineering task</h2>
<p class="hint">Public GitHub URLs use analysis-only mode. This demo uses a standard browser form, so it works even when JavaScript is blocked or cached.</p>
<form method="get" action="/run-ui">
<div class="grid"><div class="field"><label for="repo">GitHub repository URL or local path</label><input id="repo" name="repo_url" required placeholder="https://github.com/owner/repository"></div>
<div class="field"><label for="request">Task</label><textarea id="request" name="request" required placeholder="Analyze this repository and explain how the health-check endpoint works."></textarea></div></div>
<div class="actions"><button type="submit">Run CodeForge</button><span class="status">Ready — submit to start</span></div>
</form>
<pre class="output">Enter a public GitHub URL and task, then press Run CodeForge. The result page will appear when analysis finishes.</pre></section>
<div class="flow">Plan → Research → Analysis Complete</div>
</main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/health")
def health():
    return {"status": "ok", "service": "codeforge", "github_repo_input": True, "public_github_mode": "analysis_only"}


@app.get("/metrics")
def metrics():
    return (
        "# HELP codeforge_runs_total Total workflow runs\n"
        "# TYPE codeforge_runs_total counter\n"
        f"codeforge_runs_total {_runs}\n"
        "# HELP codeforge_success_total Successful workflow runs\n"
        f"codeforge_success_total {_successes}\n"
    )


def _esc(value) -> str:
    return html.escape(str(value))


def _repo_name(path: str) -> str:
    cleaned = path.rstrip("/\\")
    return os.path.basename(cleaned) or "Repository"


def _workflow_steps(result: dict) -> list[tuple[str, str]]:
    phase = result.get("phase", "DONE")
    steps = [("Plan", "planned"), ("Research", "researched"), ("Analysis", "analyzed")]
    if phase == "DONE":
        return [(name, "done") for name, _ in steps]
    return [(name, "done" if i < 2 else "current") for i, (name, _) in enumerate(steps)]


def _result_page(result: dict) -> str:
    mode = result.get("mode", "LOCAL_WORKFLOW")
    success = result.get("result") == "ANALYSIS_COMPLETE" or result.get("phase") == "DONE"
    status_label = "Analysis Complete" if success else "Workflow Finished"
    status_class = "success" if success else "neutral"
    repo = _repo_name(result.get("repo_path", ""))
    request = result.get("user_request", "")
    plan = result.get("plan") or {}
    evidence = result.get("evidence") or []
    logs = result.get("logs") or []
    metadata = result.get("pr_metadata") or {}
    steps = _workflow_steps(result)

    evidence_html = ""
    if evidence:
        cards = []
        for item in evidence[:8]:
            path = _esc(item.get("file_path", ""))
            start = item.get("start_line", "?")
            end = item.get("end_line", "?")
            symbol = item.get("symbol")
            score = item.get("relevance_score", 0)
            content = _esc(item.get("content", ""))
            cards.append(f"<div class='evidence'><div class='ev-head'><strong>{path}</strong><span>Lines {start}–{end}</span></div>{'<div class=\"symbol\">'+_esc(symbol)+'</div>' if symbol else ''}<pre>{content}</pre><div class='score'>Relevance {float(score):.2f}</div></div>")
        evidence_html = "<section><div class='section-title'>🔎 Repository Evidence</div><div class='evidence-grid'>" + "".join(cards) + "</div></section>"
    else:
        evidence_html = "<section><div class='section-title'>🔎 Repository Evidence</div><div class='empty'>No evidence snippets were returned for this request.</div></section>"

    logs_html = "".join(f"<div>{_esc(line)}</div>" for line in logs[-12:])
    raw = html.escape(json.dumps(result, indent=2, ensure_ascii=False))
    plan_summary = plan.get("summary") or "Repository analysis completed."
    note = result.get("note") or metadata.get("message") or ""
    mode_label = "Public GitHub · Analysis Only" if mode == "PUBLIC_GITHUB_PREVIEW" else "Local Workspace · Full Workflow"

    step_html = "".join(
        f"<div class='step'><span class='dot'>✓</span><span>{_esc(name)}</span></div>" if state == "done" else
        f"<div class='step current'><span class='dot'>•</span><span>{_esc(name)}</span></div>"
        for name, state in steps
    )

    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>CodeForge Result</title>
<style>
:root{{--bg:#070a12;--panel:#101625;--border:#26324d;--muted:#9eacd0;--text:#f4f7ff;--accent:#8b9cff;--good:#61d095}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top,#11182a 0,#070a12 42%);color:var(--text);font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1040px;margin:auto;padding:28px 18px 60px}}a{{color:#b8c3e6;text-decoration:none}}a:hover{{text-decoration:underline}}.top{{margin-bottom:22px}}.hero{{background:linear-gradient(135deg,#121a2c,#0d1321);border:1px solid var(--border);border-radius:22px;padding:25px;box-shadow:0 20px 60px rgba(0,0,0,.25)}}.eyebrow{{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}}h1{{font-size:38px;margin:7px 0 8px}}.subtitle{{margin:0;color:var(--muted);line-height:1.55;word-break:break-word}}.status{{display:inline-flex;align-items:center;gap:8px;margin-top:18px;padding:8px 12px;border-radius:999px;font-weight:800;font-size:13px}}.success{{background:rgba(97,208,149,.12);color:#7be0a8;border:1px solid rgba(97,208,149,.25)}}.neutral{{background:rgba(139,156,255,.12);color:#b9c4ff;border:1px solid rgba(139,156,255,.25)}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px}}.meta-card{{background:#0a0f1c;border:1px solid #202b43;border-radius:12px;padding:13px}}.meta-card small{{display:block;color:#7f8baa;font-size:11px;text-transform:uppercase;font-weight:800;margin-bottom:5px}}.meta-card div{{word-break:break-word}}section{{margin-top:18px;background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:20px}}.section-title{{font-size:17px;font-weight:850;margin-bottom:13px}}.flow{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.step{{display:flex;align-items:center;gap:9px;padding:12px;border-radius:11px;background:#0a0f1c;border:1px solid #202b43;color:#c9d2e9;font-weight:700}}.dot{{display:grid;place-items:center;width:23px;height:23px;border-radius:50%;background:rgba(97,208,149,.14);color:var(--good);font-weight:900}}.step.current .dot{{background:rgba(139,156,255,.14);color:var(--accent)}}.summary{{color:#d9e0f0;line-height:1.65;margin:0}}.evidence-grid{{display:grid;gap:12px}}.evidence{{background:#090e19;border:1px solid #202b43;border-radius:13px;padding:14px}}.ev-head{{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:13px}}.ev-head strong{{word-break:break-all}}.ev-head span,.score{{color:#8290ae;font-size:12px}}.symbol{{margin-top:7px;color:#aab7dc;font-size:12px}}.evidence pre{{margin:10px 0 8px;padding:11px;background:#050810;border-radius:9px;overflow:auto;white-space:pre-wrap;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#dce4f5}}.empty{{color:var(--muted);padding:10px 0}}details{{border:1px solid #202b43;border-radius:12px;background:#090e19;padding:2px 12px}}summary{{cursor:pointer;padding:13px;font-weight:800}}details pre{{white-space:pre-wrap;overflow:auto;max-height:520px;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#cbd5ea}}.logs{{font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;color:#aebbd5;max-height:240px;overflow:auto;background:#070a12;border-radius:10px;padding:12px}}.note{{margin-top:12px;padding:12px;border-left:3px solid var(--accent);background:#0a0f1c;color:#aebbd5;line-height:1.5}}.back{{display:inline-block;margin-bottom:14px}}@media(max-width:700px){{main{{padding:18px 12px 40px}}h1{{font-size:31px}}.meta,.flow{{grid-template-columns:1fr}}section{{padding:16px}}.ev-head{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><main>
<div class='top'><a class='back' href='/'>← Back to CodeForge</a></div>
<div class='hero'>
<div class='eyebrow'>⚒ CodeForge Engineering Report</div>
<h1>✓ {status_label}</h1>
<p class='subtitle'>{_esc(request)}</p>
<div class='status {status_class}'>● {_esc(mode_label)}</div>
<div class='meta'><div class='meta-card'><small>Repository</small><div>{_esc(repo)}</div></div><div class='meta-card'><small>Task ID</small><div>{_esc(result.get('task_id','—'))}</div></div></div>
</div>
<section><div class='section-title'>Workflow</div><div class='flow'>{step_html}</div></section>
<section><div class='section-title'>🧠 Analysis Summary</div><p class='summary'>{_esc(plan_summary)}</p>{f"<div class='note'>{_esc(note)}</div>" if note else ''}</section>
{evidence_html}
<section><div class='section-title'>📋 Execution Log</div><div class='logs'>{logs_html or '<div>No execution log entries.</div>'}</div></section>
<section><details><summary>View Raw JSON</summary><pre>{raw}</pre></details></section>
</main></body></html>"""


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
        return HTMLResponse(f"<h2>CodeForge failed</h2><pre>{html.escape(str(exc))}</pre><p><a href='/'>Back to CodeForge</a></p>", status_code=502)
    except Exception as exc:
        return HTMLResponse(f"<h2>CodeForge execution failed</h2><pre>{html.escape(type(exc).__name__)}</pre><p><a href='/'>Back to CodeForge</a></p>", status_code=500)


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
