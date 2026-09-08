"""Command-line entry point for CodeForge."""
import argparse
import json
import os
from codeforge.core.security.security_policy import SecurityPolicyEngine
from codeforge.ingestion.ast_parser import RepositoryScanner

def scan_repository(path: str):
    scanner = RepositoryScanner(path)
    chunks = scanner.scan()
    return {"files": len({c.file_path for c in chunks}), "chunks": len(chunks)}

def security_scan(path: str):
    scanner = RepositoryScanner(path)
    chunks = scanner.scan()
    findings = []
    for chunk in chunks:
        if chunk.symbol is None:
            findings.extend(SecurityPolicyEngine.scan_content(chunk.file_path, chunk.content))
    return findings

def main() -> int:
    parser = argparse.ArgumentParser(prog="codeforge", description="Security-conscious repository research and coding-agent foundation")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan a repository")
    scan.add_argument("path", nargs="?", default=".")
    sec = sub.add_parser("security", help="scan source files for security findings")
    sec.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()
    path = os.path.abspath(args.path)
    if args.command == "scan":
        print(json.dumps(scan_repository(path), indent=2)); return 0
    findings = security_scan(path)
    print(json.dumps([f.model_dump() if hasattr(f, "model_dump") else f.dict() for f in findings], indent=2))
    return 1 if findings else 0

if __name__ == "__main__":
    raise SystemExit(main())
