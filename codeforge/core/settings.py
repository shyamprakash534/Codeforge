"""CodeForge Configuration Settings."""
import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class LLMSettings:
    provider: str = os.getenv("CODEFORGE_LLM_PROVIDER", "local")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name: str = os.getenv("CODEFORGE_MODEL", "qwen2.5-coder:7b")
    temperature: float = 0.1
    timeout_seconds: int = 60

@dataclass
class SandboxSettings:
    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    max_stdout_bytes: int = 65536
    allowed_commands: List[str] = field(default_factory=lambda: ["pytest", "python3 -m unittest", "python -m unittest", "flake8", "python3", "python"])

@dataclass
class RetrievalSettings:
    top_k: int = 5
    dense_weight: float = 0.6
    lexical_weight: float = 0.4
    min_relevance_score: float = 0.15

@dataclass
class SecuritySettings:
    block_hardcoded_secrets: bool = True
    block_unsafe_eval: bool = True
    block_path_traversal: bool = True
    enforce_workspace_confinement: bool = True
    max_retry_budget: int = 3

@dataclass
class ObservabilitySettings:
    trace_dir: str = os.getenv("CODEFORGE_TRACE_DIR", "./traces")
    export_to_json: bool = True

@dataclass
class CodeForgeConfig:
    llm: LLMSettings = field(default_factory=LLMSettings)
    sandbox: SandboxSettings = field(default_factory=SandboxSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = field(default_factory=ObservabilitySettings)

settings = CodeForgeConfig()
