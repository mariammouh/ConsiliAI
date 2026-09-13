"""
Shared Embedding Model Module
=============================
Provides a singleton SentenceTransformer instance for generating dense vector
embeddings across the entire ConsiliAI application.

Model: 'all-MiniLM-L6-v2' (384 dimensions).
Used by ChromaDB collections (user_docs, search_cache, analysis_cache) and
novelty analysis cosine similarity calculations.
"""

from sentence_transformers import SentenceTransformer

# Load the model once on startup and reuse across all threads to conserve memory
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')


def embed(text: str) -> list:
    """
    Generate a 384-dimensional dense vector embedding for the input text.
    
    Args:
        text: Input string to embed.
        
    Returns:
        List of floats representing the embedding vector.
    """
    return EMBEDDING_MODEL.encode(text).tolist()