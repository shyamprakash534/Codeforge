"""Workspace File and Code Manipulation Tools with Path Confinement."""
import difflib
import fnmatch
import os
from typing import List, Optional
from pydantic import BaseModel
from codeforge.core.tools.base import BaseTool, ToolRole, ToolResult

def resolve_safe_path(repo_path: str, rel_path: str) -> str:
    """Resolve a workspace path and reject traversal outside the repository."""
    abs_repo = os.path.realpath(repo_path)
    target = os.path.realpath(os.path.join(abs_repo, rel_path))
    try:
        inside = os.path.commonpath([abs_repo, target]) == abs_repo
    except ValueError:
        inside = False
    if not inside:
        raise PermissionError(f"Path traversal blocked: '{rel_path}' is outside workspace '{abs_repo}'")
    return target

class ReadFileArgs(BaseModel):
    rel_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads content or specific lines of a file within the workspace."
    allowed_roles = [ToolRole.RESEARCHER, ToolRole.CODER, ToolRole.TEST_ENGINEER, ToolRole.REVIEWER, ToolRole.ORCHESTRATOR]
    args_schema = ReadFileArgs
    def __init__(self, repo_path: str): self.repo_path = repo_path
    def _run(self, rel_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
        try:
            full_path = resolve_safe_path(self.repo_path, rel_path)
            if not os.path.isfile(full_path): return ToolResult(success=False, error=f"File '{rel_path}' does not exist.")
            with open(full_path, "r", encoding="utf-8", errors="replace") as f: lines = f.readlines()
            total = len(lines); start = max(1, start_line or 1); end = min(total, end_line or total)
            if start > end and total: return ToolResult(success=False, error="start_line must not exceed end_line")
            return ToolResult(success=True, data={"file_path": rel_path, "content": "".join(lines[start-1:end]), "start_line": start, "end_line": end, "total_lines": total})
        except Exception as exc: return ToolResult(success=False, error=str(exc))

class ListFilesArgs(BaseModel):
    pattern: str = "*"

class ListFilesTool(BaseTool):
    name = "list_files"
    description = "Lists files in workspace matching a pattern."
    allowed_roles = [ToolRole.RESEARCHER, ToolRole.CODER, ToolRole.ORCHESTRATOR]
    args_schema = ListFilesArgs
    def __init__(self, repo_path: str): self.repo_path = repo_path
    def _run(self, pattern: str = "*") -> ToolResult:
        matches = []; root_base = os.path.realpath(self.repo_path)
        for root, dirs, files in os.walk(root_base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv", "node_modules")]
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), root_base)
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern): matches.append(rel)
        return ToolResult(success=True, data={"files": sorted(matches)})

class WriteFileArgs(BaseModel):
    rel_path: str
    content: str

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Writes or replaces a complete file inside the workspace (CODER role only)."
    allowed_roles = [ToolRole.CODER]
    args_schema = WriteFileArgs
    def __init__(self, repo_path: str): self.repo_path = repo_path
    def _run(self, rel_path: str, content: str) -> ToolResult:
        try:
            full_path = resolve_safe_path(self.repo_path, rel_path); os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f: f.write(content)
            return ToolResult(success=True, data={"file_path": rel_path, "bytes_written": len(content.encode("utf-8"))})
        except Exception as exc: return ToolResult(success=False, error=str(exc))

class ApplyPatchArgs(BaseModel):
    rel_path: str
    target_snippet: str
    replacement_snippet: str

class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    description = "Replaces a specific snippet in an existing file with an updated snippet (CODER role only)."
    allowed_roles = [ToolRole.CODER]
    args_schema = ApplyPatchArgs
    def __init__(self, repo_path: str): self.repo_path = repo_path
    def _run(self, rel_path: str, target_snippet: str, replacement_snippet: str) -> ToolResult:
        try:
            full_path = resolve_safe_path(self.repo_path, rel_path)
            if not os.path.isfile(full_path): return ToolResult(success=False, error=f"Target file '{rel_path}' not found.")
            with open(full_path, "r", encoding="utf-8") as f: original = f.read()
            if target_snippet not in original: return ToolResult(success=False, error=f"Target snippet not found in '{rel_path}'. Verify original lines before patching.")
            modified = original.replace(target_snippet, replacement_snippet, 1)
            with open(full_path, "w", encoding="utf-8") as f: f.write(modified)
            diff = "".join(difflib.unified_diff(original.splitlines(True), modified.splitlines(True), fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"))
            return ToolResult(success=True, data={"file_path": rel_path, "diff": diff})
        except Exception as exc: return ToolResult(success=False, error=str(exc))
