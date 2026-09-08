"""Security tool facade over the CodeForge security policy engine."""
import os
from codeforge.core.security.security_policy import SecurityPolicyEngine
class SecurityTool:
    def __init__(self, repo_path:str): self.repo_path=os.path.abspath(repo_path)
    def scan_file(self, rel_path:str):
        path=os.path.abspath(os.path.join(self.repo_path,rel_path))
        if os.path.commonpath([self.repo_path,path]) != self.repo_path: raise PermissionError('Path outside workspace')
        with open(path,encoding='utf-8',errors='replace') as f: return SecurityPolicyEngine.scan_content(rel_path,f.read())
    def scan_diff(self,diff:str): return SecurityPolicyEngine.scan_diff(diff)
    def scan_repository(self):
        findings=[]
        for root,dirs,files in os.walk(self.repo_path):
            dirs[:]=[d for d in dirs if d not in {'.git','.venv','venv','node_modules','__pycache__'}]
            for name in files:
                path=os.path.join(root,name); rel=os.path.relpath(path,self.repo_path)
                try:
                    with open(path,encoding='utf-8',errors='replace') as f: findings.extend(SecurityPolicyEngine.scan_content(rel,f.read()))
                except OSError: pass
        return findings
