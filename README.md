# CodeForge — Autonomous Software Factory

CodeForge turns a high-level software request into a controlled engineering workflow: **plan → research → architect → code → test → debug → review → security → approval**.

## Architecture

- **Agents:** Planner, Repository Researcher, Architect, Coder, Tester, Debugger, Reviewer
- **Orchestration:** typed `TaskState` workflow with explicit phases and retry budget
- **RAG:** AST-aware repository ingestion + hybrid lexical retrieval; optional ChromaDB adapter
- **Local LLM:** optional Ollama client (no hosted API required)
- **Tools:** workspace/file, Git, safe shell, test runner, Docker sandbox, database, security, web search, GitHub PR
- **Security:** RBAC, workspace confinement, secret detection, dangerous-call detection, path traversal checks, prompt-injection patterns, human approval gate
- **Interfaces:** CLI, optional FastAPI API, optional Streamlit UI
- **Observability:** structured task logs, trace spans, evaluation reports
- **Infrastructure:** Dockerfile and Docker Compose for local Ollama-backed operation

## Quick start

```bash
python -m pip install -e '.[dev]'
codeforge scan .
codeforge security .
codeforge run "Add a health endpoint" --repo .
```

### Optional interfaces

```bash
python -m pip install -e '.[api]'
uvicorn codeforge.api.main:app --reload
```

```bash
python -m pip install -e '.[ui]'
streamlit run codeforge/ui/streamlit_app.py
```

### Local LLM

Set `CODEFORGE_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`, and `CODEFORGE_MODEL` when you want the local Ollama adapter. The core workflow remains usable without an LLM service.

### Docker

```bash
docker compose up --build
```

## Safe code changes

The Coder agent accepts explicit patch suggestions rather than executing unrestricted generated code. Execution tools use `shell=False`, allow-lists, timeouts, and (when enabled) a network-isolated Docker sandbox. Sensitive changes can remain pending until a human approval is supplied.

## Tests

```bash
python -m pytest
```

CI runs the test suite on pushes and pull requests.

## Project layout

```text
codeforge/
  agents/              # Planner, Researcher, Architect, Coder, Tester, Debugger, Reviewer
  api/                 # FastAPI interface
  approval/            # Human-in-the-loop gate
  core/                # State, settings, retrieval, security, orchestration, tools
  evaluation/          # Evaluation reports and metrics
  ingestion/           # Repository AST/source scanner
  llm/                 # Local Ollama adapter
  observability/       # JSON trace collector
  tools/               # Git, test, shell, Docker, DB, security, web, GitHub tools
  ui/                  # Streamlit interface

tests/
Dockerfile
docker-compose.yml
pyproject.toml
```

## Design goal

CodeForge is designed as a **local-first, security-conscious software factory**. External services are optional adapters, not hidden requirements.
