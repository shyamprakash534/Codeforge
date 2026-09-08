"""Coder Agent: performs safe targeted patch-based edits on workspace files."""
from typing import Optional
from codeforge.core.state import TaskState, TaskPhase, FileChange
from codeforge.core.tools.base import ToolRole
from codeforge.core.tools.workspace_tools import ApplyPatchTool, WriteFileTool
from codeforge.observability.tracer import TraceCollector

class CoderAgent:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.patch_tool = ApplyPatchTool(repo_path)
        self.write_tool = WriteFileTool(repo_path)

    def run(self, state: TaskState, tracer: TraceCollector, patch_suggestion: Optional[dict] = None) -> TaskState:
        span = tracer.start_span("agent.coder", span_type="agent")
        try:
            state.phase = TaskPhase.IMPLEMENT
            state.log("Applying code modifications to workspace...")
            if not patch_suggestion:
                state.log("No patch suggestion supplied; no files changed.")
                return state
            rel_path = patch_suggestion.get("file_path")
            target = patch_suggestion.get("target_snippet")
            replacement = patch_suggestion.get("replacement_snippet")
            full_content = patch_suggestion.get("full_content")
            if rel_path and full_content is not None:
                res = self.write_tool.execute(ToolRole.CODER, rel_path=rel_path, content=full_content)
                if not res.success: state.log(f"Write tool error: {res.error}"); return state
                state.changed_files.append(FileChange(file_path=rel_path, action="edit", new_snippet=full_content, diff=f"Updated full content of {rel_path}"))
                state.log(f"Updated full content for {rel_path}")
            elif rel_path and target is not None and replacement is not None:
                res = self.patch_tool.execute(ToolRole.CODER, rel_path=rel_path, target_snippet=target, replacement_snippet=replacement)
                if not res.success: state.log(f"Patch tool error: {res.error}"); return state
                diff_str = res.data.get("diff", "")
                state.changed_files.append(FileChange(file_path=rel_path, action="edit", original_snippet=target, new_snippet=replacement, diff=diff_str))
                state.diff += "\n" + diff_str
                state.log(f"Successfully applied patch to '{rel_path}'")
            else:
                state.log("Invalid patch suggestion: expected file_path plus full_content or target/replacement snippets.")
            return state
        finally:
            tracer.end_span(span.span_id)
