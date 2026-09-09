"""Safe Git integration used by the workflow's patch/PR stage."""
import os, re, subprocess

class GitTool:
    def __init__(self,repo_path:str): self.repo_path=os.path.abspath(repo_path)
    def _run(self,args,timeout=60):
        p=subprocess.run(['git',*args],cwd=self.repo_path,capture_output=True,text=True,shell=False,timeout=timeout)
        return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    def status(self): return self._run(['status','--short'])
    def diff(self): return self._run(['diff','--'])
    def branch(self,name):
        if not re.fullmatch(r'[A-Za-z0-9._/-]{1,100}',name) or name.startswith(('-','.')): return {'ok':False,'error':'Invalid branch name.'}
        return self._run(['switch','-c',name])
    def commit(self,message):
        add=self._run(['add','-A'])
        if not add['ok']: return add
        return self._run(['commit','-m',message])
    def push(self,branch): return self._run(['push','-u','origin',branch],timeout=120)
    def remote_url(self): return self._run(['remote','get-url','origin'])
    def log(self,limit=10): return self._run(['log',f'-{limit}','--oneline'])
