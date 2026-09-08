"""Lightweight Python repository scanner used by the researcher agent."""
import ast
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CodeChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    symbol: Optional[str] = None
    doc_type: str = "code"

class RepositoryScanner:
    """Indexes supported source files without executing repository code."""
    SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".md", ".txt", ".json", ".yaml", ".yml"}

    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.chunks: List[CodeChunk] = []

    def scan(self) -> List[CodeChunk]:
        self.chunks = []
        if not os.path.isdir(self.repo_path):
            raise FileNotFoundError(f"Repository path not found: {self.repo_path}")
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS and not d.startswith(".")]
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() not in self.EXTENSIONS:
                    continue
                path = os.path.join(root, name)
                rel = os.path.relpath(path, self.repo_path)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f: text = f.read()
                except OSError:
                    continue
                if not text.strip(): continue
                self._add_file(rel, text)
        return self.chunks

    def _add_file(self, rel: str, text: str) -> None:
        lines = text.splitlines()
        if rel.endswith(".py"):
            try:
                tree = ast.parse(text)
                nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                for node in sorted(nodes, key=lambda n: (getattr(n, "lineno", 1), getattr(n, "end_lineno", getattr(n, "lineno", 1)))):
                    start = node.lineno; end = getattr(node, "end_lineno", start)
                    self.chunks.append(CodeChunk(rel, start, end, "\n".join(lines[start-1:end]), node.name))
            except SyntaxError:
                pass
        self.chunks.append(CodeChunk(rel, 1, len(lines), text, None, "code"))
