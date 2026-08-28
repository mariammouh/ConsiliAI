import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from .chroma_client import collection

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "user_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def simple_text_splitter(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    A minimal recursive character splitter that keeps things readable.
    It splits on double newline, then single newline, then space, then character.
    """
    separators = ["\n\n", "\n", ". ", " ", ""]
    chunks = [text]
    for sep in separators:
        new_chunks = []
        for chunk in chunks:
            if len(chunk) <= chunk_size:
                new_chunks.append(chunk)
            else:
                parts = chunk.split(sep)
                # Add separator back (except for empty string)
                if sep:
                    parts = [p + sep for p in parts[:-1]] + [parts[-1]]
                new_chunks.extend(parts)
        chunks = new_chunks

    # Merge short chunks and split oversized ones
    final_chunks = []
    current = ""
    for chunk in chunks:
        if len(current) + len(chunk) <= chunk_size:
            current += chunk
        else:
            if current:
                final_chunks.append(current.strip())
            # If a single chunk is too big, split further by fixed length
            while len(chunk) > chunk_size:
                final_chunks.append(chunk[:chunk_size].strip())
                chunk = chunk[chunk_size - overlap:]
            current = chunk
    if current.strip():
        final_chunks.append(current.strip())
    return final_chunks


def process_pdf(file_path: str, user_id: str, conversation_id: str = None, chunk_size: int = 500, chunk_overlap: int = 50):
    # 1. Extract text
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Basic cleaning
    text = " ".join(text.split())
    if not text.strip():
        return 0

    # 2. Split into chunks (custom, no LangChain)
    chunks = simple_text_splitter(text, chunk_size, chunk_overlap)

    # 3. Embed & store
    file_name = os.path.basename(file_path)
    owner_key = conversation_id if conversation_id else user_id
    for i, chunk in enumerate(chunks):
        embedding = embedding_model.encode(chunk).tolist()
        metadata = {
            "source": file_name,
            "chunk_id": i,
            "user_id": str(user_id)
        }
        if conversation_id:
            metadata["conversation_id"] = str(conversation_id)

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[f"{owner_key}_{file_name}_{i}"]
        )
    return len(chunks)