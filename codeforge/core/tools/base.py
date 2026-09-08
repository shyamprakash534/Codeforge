"""Base Tool Interfaces and Role-Based Access Control (RBAC)."""
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

class ToolRole(str, Enum):
    RESEARCHER = "RESEARCHER"
    CODER = "CODER"
    TEST_ENGINEER = "TEST_ENGINEER"
    REVIEWER = "REVIEWER"
    SECURITY = "SECURITY"
    ORCHESTRATOR = "ORCHESTRATOR"

class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseTool:
    """Abstract base tool enforcing strict RBAC and argument validation."""
    name: str = "base_tool"
    description: str = "Base tool"
    allowed_roles: List[ToolRole] = [ToolRole.ORCHESTRATOR]
    args_schema: Optional[Type[BaseModel]] = None

    def execute(self, caller_role: ToolRole, **kwargs) -> ToolResult:
        if caller_role not in self.allowed_roles:
            return ToolResult(success=False, error=f"Permission Denied: Role {caller_role.value} is not authorized to use tool '{self.name}'.")
        if self.args_schema:
            try:
                validated_args = self.args_schema(**kwargs)
                values = validated_args.model_dump() if hasattr(validated_args, "model_dump") else validated_args.dict()
                return self._run(**values)
            except Exception as exc:
                return ToolResult(success=False, error=f"Invalid arguments for tool '{self.name}': {exc}")
        return self._run(**kwargs)

    def _run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
