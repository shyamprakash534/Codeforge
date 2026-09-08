"""Restricted command execution; no shell interpretation."""
import os, subprocess

class SafeShell:
    # Python is intentionally excluded: `python -c` can bypass an executable allow-list.
    ALLOWED = {'pytest', 'git'}
    GIT_SUBCOMMANDS = {'status','diff','log','branch','switch','add','commit'}
    def __init__(self, repo_path: str, timeout: int = 30): self.repo_path=os.path.abspath(repo_path); self.timeout=timeout
    def run(self, command: list[str]) -> dict:
        if not command or command[0] not in self.ALLOWED: return {'ok':False,'error':'Command is not allow-listed.'}
        if command[0]=='git' and (len(command)<2 or command[1] not in self.GIT_SUBCOMMANDS):
            return {'ok':False,'error':'Git subcommand is not allow-listed.'}
        if command[0]=='git' and any(arg in {'--exec-path','--upload-pack','--receive-pack'} or arg.startswith(('--config','-c')) for arg in command[2:]):
            return {'ok':False,'error':'Potentially unsafe git options are blocked.'}
        try:
            p=subprocess.run(command,cwd=self.repo_path,capture_output=True,text=True,timeout=self.timeout,shell=False)
            return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout[-65536:],'stderr':p.stderr[-65536:]}
        except subprocess.TimeoutExpired: return {'ok':False,'exit_code':124,'error':'Command timed out.'}
