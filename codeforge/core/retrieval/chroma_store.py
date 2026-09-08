"""Optional ChromaDB vector-store adapter with a clear dependency boundary."""
class ChromaStore:
    def __init__(self,path='./data/chroma',collection='codeforge'):
        try: import chromadb
        except ImportError as exc: raise RuntimeError("Install the 'rag' extra to use ChromaDB") from exc
        self.client=chromadb.PersistentClient(path=path); self.collection=self.client.get_or_create_collection(collection)
    def upsert(self,ids,documents,metadatas): self.collection.upsert(ids=ids,documents=documents,metadatas=metadatas)
    def query(self,texts,n_results=5): return self.collection.query(query_texts=texts,n_results=n_results)
