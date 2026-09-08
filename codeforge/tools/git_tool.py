"""Git integration for status, diff, branches, commits and PR preparation."""
import os, subprocess
class GitTool:
    def __init__(self, repo_path: str): self.repo_path=os.path.abspath(repo_path)
    def _run(self,args):
        p=subprocess.run(['git',*args],cwd=self.repo_path,capture_output=True,text=True,shell=False)
        return {'ok':p.returncode==0,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    def status(self): return self._run(['status','--short'])
    def diff(self): return self._run(['diff','--'])
    def branch(self,name): return self._run(['switch','-c',name])
    def commit(self,message):
        add=self._run(['add','-A']);
        if not add['ok']: return add
        return self._run(['commit','-m',message])
    def log(self,limit=10): return self._run(['log',f'-{limit}','--oneline'])
