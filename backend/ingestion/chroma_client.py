"""
ChromaDB Storage & Semantic Cache Client
========================================
Manages persistent ChromaDB vector collections for ConsiliAI:
  1. `user_docs`: Stores chunked embeddings of user-uploaded PDFs for personal RAG.
  2. `search_cache`: Semantic cache for academic paper searches using cosine distance.
  3. `analysis_cache`: Content-hash based cache for paper section analysis extractions.
"""

import chromadb
import os
from .embedding_model import embed   # Shared 384-d sentence-transformers model

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Document chunks collection for user RAG
collection = chroma_client.get_or_create_collection(name="user_docs")

# Semantic cache collection for search queries (cosine distance metric)
cache_collection = chroma_client.get_or_create_collection(
    name="search_cache",
    metadata={"hnsw:space": "cosine"}   # Cosine similarity metric
)

# Content-hash cache collection for extracted paper sections
analysis_cache_collection = chroma_client.get_or_create_collection("analysis_cache")

def query_chroma(query_text: str, user_id: str, n_results: int = 3):
    """
    Query the ChromaDB `user_docs` collection for semantic chunks relevant to query_text.
    
    Implements a 3-tier fallback strategy:
      1. Match where either user_id OR conversation_id equals the provided identifier.
      2. Fall back to exact user_id metadata match.
      3. Fall back to unconstrained top-similarity search across the collection.
    
    Args:
        query_text: Natural language query string.
        user_id: User UUID or Conversation ID string.
        n_results: Maximum number of document chunks to retrieve (default: 3).
        
    Returns:
        List of matching document text chunks.
    """
    query_embedding = embed(query_text)
    # 1. Try matching user_id or conversation_id against the passed user_id (which might be thread_id)
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"$or": [{"user_id": str(user_id)}, {"conversation_id": str(user_id)}]}
        )
        docs = results['documents'][0] if (results and results.get('documents') and results['documents']) else []
        if docs:
            return docs
    except Exception:
        pass

    # 2. Fallback: query with simple user_id filter
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"user_id": str(user_id)}
        )
        docs = results['documents'][0] if (results and results.get('documents') and results['documents']) else []
        if docs:
            return docs
    except Exception:
        pass

    # 3. Final fallback: return top matching docs in collection if any exist
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results['documents'][0] if (results and results.get('documents') and results['documents']) else []
    except Exception:
        return []


def delete_conversation_documents(conversation_id: str) -> set[str]:
    """
    Delete all document chunks belonging to a specific conversation from ChromaDB.
    Scans by both metadata (conversation_id) and document ID prefix (e.g. {conversation_id}_...).
    
    Returns:
        The set of source filenames whose chunks were removed.
    """
    deleted_sources = set()
    ids_to_delete = set()
    cid_str = str(conversation_id)

    try:
        # Match by metadata
        res = collection.get(where={"conversation_id": cid_str})
        if res and res.get("ids"):
            ids_to_delete.update(res["ids"])
            for meta in res.get("metadatas") or []:
                if meta and meta.get("source"):
                    deleted_sources.add(meta["source"])
    except Exception as e:
        # print(f"[chroma] Error querying chunks for conversation {conversation_id}: {e}")
        pass

    try:
        # Match by ID prefix
        all_items = collection.get()
        if all_items and all_items.get("ids"):
            for idx, doc_id in enumerate(all_items["ids"]):
                if doc_id.startswith(f"{cid_str}_"):
                    ids_to_delete.add(doc_id)
                    meta = all_items["metadatas"][idx] if all_items.get("metadatas") else None
                    if meta and meta.get("source"):
                        deleted_sources.add(meta["source"])
    except Exception as e:
        # print(f"[chroma] Error scanning ID prefix for conversation {conversation_id}: {e}")
        pass

    if ids_to_delete:
        try:
            collection.delete(ids=list(ids_to_delete))
            # print(f"[chroma] Deleted {len(ids_to_delete)} chunks for conversation {conversation_id}")
        except Exception as e:
            # print(f"[chroma] Error deleting chunks for conversation {conversation_id}: {e}")
            pass

    return deleted_sources


def delete_user_documents(user_id: str, conversation_ids: list[str] = None) -> set[str]:
    """
    Delete all document chunks belonging to a user (and all their conversations) from ChromaDB.
    
    Args:
        user_id: UUID string of the target user.
        conversation_ids: Optional list of conversation IDs belonging to the user.
        
    Returns:
        The set of source filenames whose chunks were deleted.
    """
    deleted_sources = set()
    ids_to_delete = set()
    uid_str = str(user_id)
    target_keys = {uid_str}
    if conversation_ids:
        target_keys.update(str(cid) for cid in conversation_ids)

    # 1. By user_id metadata
    try:
        res = collection.get(where={"user_id": uid_str})
        if res and res.get("ids"):
            ids_to_delete.update(res["ids"])
            for meta in res.get("metadatas") or []:
                if meta and meta.get("source"):
                    deleted_sources.add(meta["source"])
    except Exception as e:
        # print(f"[chroma] Error querying chunks for user {user_id}: {e}")
        pass

    # 2. By conversation_ids metadata
    if conversation_ids:
        for cid in conversation_ids:
            try:
                res = collection.get(where={"conversation_id": str(cid)})
                if res and res.get("ids"):
                    ids_to_delete.update(res["ids"])
                    for meta in res.get("metadatas") or []:
                        if meta and meta.get("source"):
                            deleted_sources.add(meta["source"])
            except Exception:
                pass

    # 3. By ID prefix matching user_id or any conversation_id
    try:
        all_items = collection.get()
        if all_items and all_items.get("ids"):
            for idx, doc_id in enumerate(all_items["ids"]):
                if any(doc_id.startswith(f"{key}_") for key in target_keys):
                    ids_to_delete.add(doc_id)
                    meta = all_items["metadatas"][idx] if all_items.get("metadatas") else None
                    if meta and meta.get("source"):
                        deleted_sources.add(meta["source"])
    except Exception as e:
        # print(f"[chroma] Error scanning ID prefix for user {user_id}: {e}")
        pass

    if ids_to_delete:
        try:
            collection.delete(ids=list(ids_to_delete))
            # print(f"[chroma] Deleted {len(ids_to_delete)} chunks for user {user_id}")
        except Exception as e:
            # print(f"[chroma] Error deleting chunks for user {user_id}: {e}")
            pass

    return deleted_sources


def get_conversation_document_sources(conversation_id: str, user_id: str = None) -> list[str]:
    """
    Returns a sorted list of unique document source filenames associated with
    a conversation_id or user_id in ChromaDB.
    
    Checks metadata fields first; if none are found, falls back to inspecting document
    ID prefixes to support legacy chunks created before conversation metadata tagging.
    """
    sources = set()
    cid_str = str(conversation_id) if conversation_id else None

    if cid_str:
        try:
            res = collection.get(where={"conversation_id": cid_str})
            if res and res.get("metadatas"):
                for meta in res["metadatas"]:
                    if meta and meta.get("source"):
                        sources.add(meta["source"])
        except Exception:
            pass

        # Fallback to ID prefix if where didn't match (e.g. legacy chunks)
        if not sources:
            try:
                all_items = collection.get()
                if all_items and all_items.get("ids"):
                    for idx, doc_id in enumerate(all_items["ids"]):
                        if doc_id.startswith(f"{cid_str}_"):
                            meta = all_items["metadatas"][idx] if all_items.get("metadatas") else None
                            if meta and meta.get("source"):
                                sources.add(meta["source"])
            except Exception:
                pass

    if not sources and user_id:
        uid_str = str(user_id)
        try:
            res = collection.get(where={"user_id": uid_str})
            if res and res.get("metadatas"):
                for meta in res["metadatas"]:
                    if meta and meta.get("source"):
                        sources.add(meta["source"])
        except Exception:
            pass

    return sorted(list(sources))



