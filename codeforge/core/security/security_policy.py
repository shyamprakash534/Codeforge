"""Security Policy Engine for CodeForge."""
import re
from typing import List
from codeforge.core.state import SecurityFinding

class SecurityPolicyEngine:
    """Static analysis for common credential, execution, traversal, and prompt-injection risks."""
    SECRET_PATTERNS = [
        (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", "hardcoded_api_key"),
        (r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH|PRIVATE)\s+KEY-----", "private_key_block"),
        (r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}['\"]", "hardcoded_password"),
        (r"(?i)ghp_[a-zA-Z0-9]{36}", "github_personal_access_token"),
        (r"(?i)AKIA[0-9A-Z]{16}", "aws_access_key_id"),
    ]
    DANGEROUS_CALLS = [
        (r"\beval\s*\(", "Use of eval() detected (arbitrary code execution risk)"),
        (r"\bexec\s*\(", "Use of exec() detected (arbitrary code execution risk)"),
        (r"\bos\.system\s*\(", "Use of os.system() detected (shell injection risk)"),
        (r"subprocess\.(Popen|run|call)\s*\([^)]*shell\s*=\s*True", "subprocess with shell=True detected (command injection risk)"),
        (r"\b__import__\s*\(", "Dynamic __import__ usage detected"),
        (r"pickle\.loads?\s*\(", "Insecure deserialization using pickle detected"),
    ]
    PATH_TRAVERSAL_PATTERNS = [
        (r"(?:^|[\\/])\.\.(?:[\\/])\.\.", "Multiple directory traversal (../../) detected"),
        (r"open\s*\(\s*['\"]/(etc|var|usr|bin|root)", "Hardcoded root path access detected"),
    ]
    PROMPT_INJECTION_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions", "Instruction override prompt injection"),
        (r"(?i)you\s+are\s+now\s+in\s+DAN\s+mode", "Jailbreak attempt"),
        (r"(?i)disregard\s+all\s+safety\s+guidelines", "Safety bypass attempt"),
        (r"(?i)exfiltrate\s+(the\s+)?(secret|token|key)", "Data exfiltration attempt"),
    ]

    @classmethod
    def _finding(cls, risk_type, severity, file_path, line, description, recommendation):
        return SecurityFinding(risk_type=risk_type, severity=severity, file_path=file_path, line_number=line, description=description, recommendation=recommendation, passed=False)

    @classmethod
    def scan_content(cls, file_path: str, content: str) -> List[SecurityFinding]:
        findings = []
        for idx, line in enumerate(content.splitlines(), 1):
            for pattern, name in cls.SECRET_PATTERNS:
                if re.search(pattern, line): findings.append(cls._finding("secret_leak", "critical", file_path, idx, f"Potential {name} found on line {idx}.", "Remove credential and retrieve it from secure environment variables."))
            for pattern, desc in cls.DANGEROUS_CALLS:
                if re.search(pattern, line): findings.append(cls._finding("dangerous_call", "high", file_path, idx, desc, "Replace with safe alternatives and avoid shell interpretation."))
            for pattern, desc in cls.PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, line): findings.append(cls._finding("path_traversal", "high", file_path, idx, desc, "Sanitize and resolve paths relative to the workspace boundary."))
            for pattern, desc in cls.PROMPT_INJECTION_PATTERNS:
                if re.search(pattern, line): findings.append(cls._finding("prompt_injection", "critical", file_path, idx, desc, "Block untrusted instruction overrides and isolate execution context."))
        return findings

    @classmethod
    def scan_diff(cls, diff: str) -> List[SecurityFinding]:
        findings = []; current_file = "unknown"
        for line in diff.splitlines():
            if line.startswith("+++ b/"): current_file = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                findings.extend(cls.scan_content(current_file, line[1:]))
        return findings
