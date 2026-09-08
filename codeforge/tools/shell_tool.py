"""Allow-listed shell command execution; no shell=True."""
import os, subprocess

class SafeShell:
    ALLOWED = {'python', 'python3', 'pytest', 'git'}
    def __init__(self, repo_path: str, timeout: int = 30): self.repo_path=os.path.abspath(repo_path); self.timeout=timeout
    def run(self, command: list[str]) -> dict:
        if not command or command[0] not in self.ALLOWED: return {'ok':False,'error':'Command is not allow-listed.'}
        try:
            p=subprocess.run(command,cwd=self.repo_path,capture_output=True,text=True,timeout=self.timeout,shell=False)
            return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout[-65536:],'stderr':p.stderr[-65536:]}
        except subprocess.TimeoutExpired: return {'ok':False,'exit_code':124,'error':'Command timed out.'}
