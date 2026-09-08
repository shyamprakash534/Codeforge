"""GitHub REST integration for creating branches and pull requests.

Authentication is supplied explicitly through GITHUB_TOKEN; credentials are never logged.
"""
import json, os, urllib.request
class GitHubTool:
    def __init__(self, token=None, api_url='https://api.github.com'):
        self.token=token or os.getenv('GITHUB_TOKEN'); self.api_url=api_url.rstrip('/')
    def _request(self,method,path,payload=None):
        if not self.token: return {'ok':False,'error':'GITHUB_TOKEN is not configured.'}
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.api_url+path,data=data,method=method,headers={'Authorization':f'Bearer {self.token}','Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'})
        try:
            with urllib.request.urlopen(req,timeout=20) as r: return {'ok':200<=r.status<300,'status':r.status,'data':json.loads(r.read().decode() or '{}')}
        except Exception as exc: return {'ok':False,'error':str(exc)}
    def create_pull_request(self,owner,repo,head,base='main',title='CodeForge change',body='Created by CodeForge.'):
        return self._request('POST',f'/repos/{owner}/{repo}/pulls',{'title':title,'head':head,'base':base,'body':body})
