"""Local Ollama client with no hosted API dependency."""
import json, urllib.request
class OllamaClient:
    def __init__(self,base_url='http://localhost:11434',model='qwen2.5-coder:7b',timeout=120): self.base_url=base_url.rstrip('/'); self.model=model; self.timeout=timeout
    def generate(self,prompt:str,temperature=0.1):
        body=json.dumps({'model':self.model,'prompt':prompt,'stream':False,'options':{'temperature':temperature}}).encode()
        req=urllib.request.Request(self.base_url+'/api/generate',data=body,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=self.timeout) as r: return json.loads(r.read().decode()).get('response','')
