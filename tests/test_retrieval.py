from pathlib import Path
from codeforge.core.retrieval.hybrid_engine import HybridRetrievalEngine
from codeforge.ingestion.ast_parser import RepositoryScanner

def test_retrieval_returns_relevant_chunk(tmp_path: Path):
    (tmp_path / "auth.py").write_text("def authenticate(user, password):\n    return user == 'admin'\n", encoding="utf-8")
    scanner = RepositoryScanner(str(tmp_path))
    scanner.scan()
    engine = HybridRetrievalEngine(scanner, min_relevance_score=0.0)
    results = engine.search("authenticate password", top_k=3)
    assert results
    assert results[0].file_path == "auth.py"
