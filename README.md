# ⚒ CodeForge — Autonomous Software Factory

> **Turn a software request into a controlled engineering workflow.**
>
> **Plan → Research → Architect → Code → Test → Debug → Review → Security → Approval**

[![CI](https://github.com/shyamprakash534/Codeforge/actions/workflows/ci.yml/badge.svg)](https://github.com/shyamprakash534/Codeforge/actions)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?logo=render&logoColor=white)](https://codeforge-3l85.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

## 🚀 Live Demo

**Try CodeForge:** https://codeforge-3l85.onrender.com

The deployed interface provides a simple way to submit a repository task and inspect the workflow result. API documentation is available at `/docs` and the health check at `/health`.

---

## What is CodeForge?

CodeForge is a security-conscious, local-first software engineering agent framework. Instead of treating code generation as a single prompt, it models software work as a sequence of explicit engineering stages.

A request moves through specialized agents:

```text
User Request
     │
     ▼
  Planner ──► Researcher ──► Architect
                              │
                              ▼
                           Coder
                              │
                              ▼
                 Tester ──► Debugger
                              │
                              ▼
                           Reviewer
                              │
                              ▼
                       Security Scan
                              │
                              ▼
                    Human Approval Gate
                              │
                              ▼
                            Done
```

## ✨ Highlights

- **Multi-agent workflow** — separate planning, research, architecture, coding, testing, debugging and review responsibilities.
- **Repository-aware reasoning** — AST/source ingestion and hybrid lexical retrieval help agents understand an existing codebase.
- **Human-in-the-loop** — sensitive changes can remain pending until explicitly approved.
- **Security-first execution** — workspace confinement, dangerous-call detection, secret detection, path traversal checks, allow-lists and timeouts.
- **Sandbox support** — optional Docker execution with network isolation and resource limits.
- **Local-first LLM support** — optional Ollama adapter so a hosted model is not a hard requirement.
- **Developer interfaces** — CLI, FastAPI and Streamlit options.
- **GitHub integration** — tooling for repository operations and pull requests.
- **Observability and evaluation** — structured task traces, metrics and evaluation reports.
- **Containerized development** — Dockerfile and Compose setup for local infrastructure.

## 🏗️ Architecture

| Layer | Components |
|---|---|
| **Interface** | FastAPI, Streamlit, CLI |
| **Orchestration** | Typed task state, workflow stages, retry budget |
| **Agents** | Planner, Researcher, Architect, Coder, Tester, Debugger, Reviewer |
| **Knowledge** | AST parser, hybrid retrieval, optional ChromaDB |
| **LLM** | Optional local Ollama adapter |
| **Tools** | Filesystem, Git, shell, tests, Docker, DB, web search, security, GitHub |
| **Safety** | Workspace confinement, secret detection, policy checks, approval gate |
| **Operations** | Logs, traces, metrics, evaluation |
| **Infrastructure** | Docker, Docker Compose, PostgreSQL service, Ollama, Prometheus, Grafana |

## 🖥️ Use the Web UI

Open the live demo and enter:

1. **Repository path** — the repository/workspace CodeForge should inspect.
2. **Task** — describe what you want changed in plain English.
3. Click **Run CodeForge**.
4. Inspect the returned workflow state and results.

For API clients, use the interactive FastAPI documentation at:

`https://codeforge-3l85.onrender.com/docs`

## ⚡ Quick Start

### CLI

```bash
python -m pip install -e '.[dev]'
codeforge scan .
codeforge security .
codeforge run "Add a health endpoint" --repo .
```

### FastAPI

```bash
python -m pip install -e '.[api]'
uvicorn codeforge.api.main:app --reload
```

Then open `http://127.0.0.1:8000`.

### Streamlit

```bash
python -m pip install -e '.[ui]'
streamlit run codeforge/ui/streamlit_app.py
```

### Full local stack

```bash
docker compose up --build
```

## 🤖 Local LLM with Ollama

Set the following environment variables when using the local Ollama adapter:

```bash
CODEFORGE_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
CODEFORGE_MODEL=<your-model>
```

The core workflow remains usable without an LLM service.

## 🔐 Security Model

CodeForge is designed to make autonomous code execution controlled rather than unrestricted.

- Repository paths are confined to the configured workspace.
- Shell execution uses explicit allow-lists, `shell=False` and timeouts.
- Git operations are restricted to approved commands/options.
- Docker sandbox execution can disable networking and limit CPU/memory.
- Security scanning checks source content for dangerous patterns and secrets.
- Prompt-injection patterns are treated as security findings.
- Approval gates can stop sensitive workflows before changes are finalized.

## 🧪 Testing

Run the test suite with:

```bash
python -m pytest
```

GitHub Actions runs automated tests on repository changes.

## 📁 Project Structure

```text
codeforge/
├── agents/              # Planner, Researcher, Architect, Coder, Tester, Debugger, Reviewer
├── api/                 # FastAPI web/API interface
├── approval/            # Human-in-the-loop approval gate
├── core/                # State, settings, retrieval, security and orchestration
├── evaluation/          # Evaluation reports and metrics
├── ingestion/           # AST/source repository scanner
├── llm/                 # Ollama adapter
├── observability/       # Structured trace collection
├── tools/               # Git, shell, test, Docker, DB, web, security, GitHub tools
└── ui/                  # Streamlit interface

tests/                   # Automated tests
Dockerfile               # Container image
 docker-compose.yml      # Local multi-service stack
pyproject.toml            # Package and dependency configuration
```

## 🛣️ Roadmap

- [x] Agent-based engineering workflow
- [x] Repository scanning and retrieval
- [x] Security controls and approval gate
- [x] FastAPI interface
- [x] Web UI and live Render deployment
- [x] Docker sandbox tooling
- [x] GitHub PR tooling
- [ ] Fully connected LangGraph execution backend
- [ ] Autonomous code → test → debug → retest loop
- [ ] End-to-end branch → commit → PR automation
- [ ] Production PostgreSQL adapter
- [ ] Expanded integration and security test suite

## 🎯 Design Goal

CodeForge aims to be a **local-first, security-conscious software factory** where external services are optional adapters rather than hidden requirements.

## License

See the repository for the current project license and contribution terms.

---

**Built as an engineering project to explore autonomous software development, agent orchestration, repository intelligence and secure code execution.**
