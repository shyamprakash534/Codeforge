"""Safe test execution tool."""
import os, shlex, subprocess, time
from codeforge.core.state import TestResult

class TestRunner:
    def __init__(self, repo_path: str, timeout: int = 120):
        self.repo_path = os.path.abspath(repo_path); self.timeout = timeout
    def run(self) -> TestResult:
        if not os.path.isdir(os.path.join(self.repo_path, 'tests')):
            return TestResult(total=0, passed=0, exit_code=0)
        cmd = ['python', '-m', 'pytest', '-q']
        start = time.monotonic()
        try:
            p = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            return TestResult(failed=1, errors=1, duration_sec=time.monotonic()-start, stderr='Test timeout', exit_code=124)
        out = p.stdout or ''; err = p.stderr or ''
        import re
        m = re.search(r'(\d+) passed', out); f = re.search(r'(\d+) failed', out); e = re.search(r'(\d+) error', out)
        passed = int(m.group(1)) if m else 0; failed = int(f.group(1)) if f else 0; errors = int(e.group(1)) if e else 0
        return TestResult(total=passed+failed+errors, passed=passed, failed=failed, errors=errors, duration_sec=time.monotonic()-start, stdout=out[-65536:], stderr=err[-65536:], exit_code=p.returncode)
