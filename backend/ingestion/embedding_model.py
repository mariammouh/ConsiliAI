from sentence_transformers import SentenceTransformer

# Load once, reuse everywhere
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def embed(text: str) -> list:
    """Return embedding as a list of floats."""
    return EMBEDDING_MODEL.encode(text).tolist()