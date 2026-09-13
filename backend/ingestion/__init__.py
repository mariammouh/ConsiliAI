"""
ConsiliAI Ingestion Package
===========================
Handles document ingestion, text extraction, semantic chunking, and vector storage.

Key Modules:
- pdf_processor: Extracts text from PDFs using PyMuPDF and recursively splits text.
- chroma_client: Manages ChromaDB vector collections (user_docs, search_cache, analysis_cache).
- embedding_model: Shared local sentence-transformers model (all-MiniLM-L6-v2) for embeddings.
- cache: SQLite-based search query caching for paper retrieval deduplication.
"""
