"""CodeForge command-line interface."""
import argparse, json, os
from codeforge.core.security.security_policy import SecurityPolicyEngine
from codeforge.ingestion.ast_parser import RepositoryScanner
from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator

def scan_repository(path):
    chunks=RepositoryScanner(path).scan(); return {'files':len({c.file_path for c in chunks}),'chunks':len(chunks)}
def security_scan(path):
    findings=[]
    for c in RepositoryScanner(path).scan():
        if c.symbol is None: findings.extend(SecurityPolicyEngine.scan_content(c.file_path,c.content))
    return findings

def main():
    parser=argparse.ArgumentParser(prog='codeforge',description='Autonomous, security-conscious software factory')
    sub=parser.add_subparsers(dest='command',required=True)
    scan=sub.add_parser('scan'); scan.add_argument('path',nargs='?',default='.')
    sec=sub.add_parser('security'); sec.add_argument('path',nargs='?',default='.')
    run=sub.add_parser('run'); run.add_argument('request'); run.add_argument('--repo',default='.'); run.add_argument('--patch-json'); run.add_argument('--approve',action='store_true')
    args=parser.parse_args(); path=os.path.abspath(getattr(args,'path',getattr(args,'repo','.')))
    if args.command=='scan': print(json.dumps(scan_repository(path),indent=2)); return 0
    if args.command=='security':
        findings=security_scan(path); print(json.dumps([f.model_dump() for f in findings],indent=2)); return 1 if findings else 0
    patch=json.loads(args.patch_json) if args.patch_json else None
    state=CodeForgeOrchestrator(path).run(args.request,patch_suggestion=patch,approved=args.approve)
    print(json.dumps(state.model_dump(),indent=2,default=str)); return 0 if state.phase.value=='DONE' else 1
if __name__=='__main__': raise SystemExit(main())
