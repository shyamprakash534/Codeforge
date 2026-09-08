from pathlib import Path
import pytest
from codeforge.core.tools.base import ToolRole
from codeforge.core.tools.workspace_tools import ReadFileTool, WriteFileTool, resolve_safe_path

def test_path_confinement(tmp_path: Path):
    with pytest.raises(PermissionError):
        resolve_safe_path(str(tmp_path), "../outside.txt")

def test_rbac_blocks_unauthorized_write(tmp_path: Path):
    tool = WriteFileTool(str(tmp_path))
    result = tool.execute(ToolRole.RESEARCHER, rel_path="x.txt", content="x")
    assert result.success is False
    assert "Permission Denied" in result.error

def test_write_and_read(tmp_path: Path):
    writer = WriteFileTool(str(tmp_path))
    assert writer.execute(ToolRole.CODER, rel_path="src/x.txt", content="hello").success
    reader = ReadFileTool(str(tmp_path))
    result = reader.execute(ToolRole.RESEARCHER, rel_path="src/x.txt")
    assert result.success
    assert result.data["content"] == "hello"
