"""Optional Docker sandbox adapter. Fails closed when Docker is unavailable."""
import os, subprocess
class DockerSandbox:
    def __init__(self, repo_path: str, image: str='python:3.12-slim', timeout:int=60): self.repo_path=os.path.abspath(repo_path); self.image=image; self.timeout=timeout
    def available(self):
        p=subprocess.run(['docker','version','--format','{{.Server.Version}}'],capture_output=True,text=True); return p.returncode==0
    def run(self, command:list[str]) -> dict:
        if not self.available(): return {'ok':False,'error':'Docker is not available.'}
        cmd=['docker','run','--rm','--network','none','--memory','512m','--cpus','1','-v',f'{self.repo_path}:/workspace:ro','-w','/workspace',self.image,*command]
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=self.timeout,shell=False)
            return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout[-65536:],'stderr':p.stderr[-65536:]}
        except subprocess.TimeoutExpired: return {'ok':False,'exit_code':124,'error':'Sandbox timeout.'}
