"""Dependency-light lexical retrieval with an interface ready for dense retrieval."""
import math
import re
from collections import Counter
from typing import List
from codeforge.core.state import Evidence
from codeforge.ingestion.ast_parser import RepositoryScanner, CodeChunk

class HybridRetrievalEngine:
    def __init__(self, scanner: RepositoryScanner, dense_weight: float = 0.6, lexical_weight: float = 0.4, min_relevance_score: float = 0.15):
        self.scanner = scanner
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight
        self.min_relevance_score = min_relevance_score
        self.index: List[CodeChunk] = []

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", text.lower())

    def build_index(self) -> None:
        self.index = list(self.scanner.chunks or self.scanner.scan())

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        if not self.index: self.build_index()
        q = Counter(self._tokens(query)); scored = []
        for chunk in self.index:
            tokens = Counter(self._tokens(chunk.content + " " + (chunk.symbol or "")))
            overlap = sum(min(q[t], tokens[t]) for t in q)
            lexical = overlap / max(1, sum(q.values()))
            qnorm = math.sqrt(sum(v*v for v in q.values())) or 1.0
            tnorm = math.sqrt(sum(v*v for v in tokens.values())) or 1.0
            cosine = sum(q[t] * tokens[t] for t in q) / (qnorm * tnorm)
            score = self.lexical_weight * lexical + self.dense_weight * cosine
            if score >= self.min_relevance_score: scored.append((score, chunk))
        scored.sort(key=lambda x: (-x[0], x[1].file_path, x[1].start_line))
        return [Evidence(file_path=c.file_path, start_line=c.start_line, end_line=c.end_line, symbol=c.symbol, content=c.content, relevance_score=round(s, 4), doc_type=c.doc_type) for s, c in scored[:top_k]]
