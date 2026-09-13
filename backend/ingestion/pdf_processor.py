"""
PDF Ingestion & Text Splitting Module
=====================================
Extracts raw text from uploaded PDF documents using PyMuPDF (fitz),
segments the text using a custom recursive hierarchical character splitter,
computes dense vector embeddings, and registers the chunks in ChromaDB.
"""

import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from .chroma_client import collection

# Directory where uploaded PDF documents are stored on disk
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "user_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Shared embedding model for vectorizing PDF chunks
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def simple_text_splitter(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    A lightweight recursive character text splitter that operates without external framework dependencies.
    
    Splits iteratively on hierarchical boundaries:
      1. Paragraph breaks ("\\n\\n")
      2. Line breaks ("\\n")
      3. Sentence endings (". ")
      4. Word spaces (" ")
      5. Character level ("")
      
    Reassembles splits while respecting `chunk_size` and preserving `overlap` for context continuity.
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
    """
    Extract, clean, chunk, embed, and store a PDF document's text into ChromaDB.

    Args:
        file_path: Path to the PDF file on disk.
        user_id: ID of the uploading user.
        conversation_id: Optional ID of the specific conversation thread.
        chunk_size: Target maximum character length per chunk.
        chunk_overlap: Overlapping character count between adjacent chunks.

    Returns:
        The total number of chunks indexed into ChromaDB.
    """
    # 1. Extract text page-by-page using PyMuPDF
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Normalize excessive whitespace and check for empty extraction
    text = " ".join(text.split())
    if not text.strip():
        return 0

    # 2. Split text into semantic chunks using the recursive splitter
    chunks = simple_text_splitter(text, chunk_size, chunk_overlap)

    # 3. Vectorize chunks with sentence-transformers and store in ChromaDB with metadata
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