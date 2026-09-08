# CodeForge

CodeForge is a security-conscious coding-agent foundation for researching a repository, applying targeted changes, testing them, and producing structured workflow state.

## Current scope

- Typed workflow state and task phases
- Role-based tool access control
- Workspace-confined file tools
- Repository AST scanning and lightweight hybrid retrieval
- Static security policy checks for secrets, dangerous calls, path traversal, and prompt injection
- Researcher and coder agents
- JSON trace collection
- Local CLI for repository scanning and security checks

## Quick start

```bash
python -m pip install -e .
python -m codeforge --help
python -m codeforge scan .
python -m codeforge security .
```

CodeForge does not execute arbitrary generated commands. Any future execution/sandbox layer should enforce the configured command allow-list, timeout, resource limits, and workspace confinement before execution.

## Project layout

```text
codeforge/
  agents/
  core/
    retrieval/
    security/
    tools/
  ingestion/
  observability/
tests/
```

## Development

```bash
python -m pytest
```

The initial implementation is intentionally dependency-light. Pydantic is used for validated state and tool arguments.
