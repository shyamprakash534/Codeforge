"""Optional web search adapter. Disabled by default for local/offline operation."""
import urllib.parse, urllib.request, json
class WebSearchTool:
    def search(self,query:str,limit:int=5):
        # Uses DuckDuckGo HTML without an API key when network access is explicitly enabled.
        url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote(query)
        req=urllib.request.Request(url,headers={'User-Agent':'CodeForge/1.0'})
        try:
            with urllib.request.urlopen(req,timeout=10) as r: data=r.read().decode('utf-8','replace')
            import re, html
            hits=[]
            for m in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',data):
                hits.append({'url':html.unescape(m.group(1)),'title':re.sub('<.*?>','',html.unescape(m.group(2)))})
                if len(hits)>=limit: break
            return hits
        except Exception as exc: return {'error':str(exc),'results':[]}
