import chromadb
import os
from .embedding_model import embed   # use shared model

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Document chunks collection (unchanged)
collection = chroma_client.get_or_create_collection(name="user_docs")

# Semantic cache collection for search queries
cache_collection = chroma_client.get_or_create_collection(
    name="search_cache",
    metadata={"hnsw:space": "cosine"}   # cosine distance
)
analysis_cache_collection = chroma_client.get_or_create_collection("analysis_cache")
def query_chroma(query_text: str, user_id: str, n_results: int = 3):
    query_embedding = embed(query_text)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"user_id": str(user_id)}
    )
    return results['documents'][0] if results['documents'] else []

