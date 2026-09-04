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
    """Delete all document chunks belonging to a specific conversation from ChromaDB.
    Returns the set of source filenames deleted."""
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
        print(f"[chroma] Error querying chunks for conversation {conversation_id}: {e}")

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
        print(f"[chroma] Error scanning ID prefix for conversation {conversation_id}: {e}")

    if ids_to_delete:
        try:
            collection.delete(ids=list(ids_to_delete))
            print(f"[chroma] Deleted {len(ids_to_delete)} chunks for conversation {conversation_id}")
        except Exception as e:
            print(f"[chroma] Error deleting chunks for conversation {conversation_id}: {e}")

    return deleted_sources


def delete_user_documents(user_id: str, conversation_ids: list[str] = None) -> set[str]:
    """Delete all document chunks belonging to a user (and all their conversations) from ChromaDB.
    Returns the set of source filenames deleted."""
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
        print(f"[chroma] Error querying chunks for user {user_id}: {e}")

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
        print(f"[chroma] Error scanning ID prefix for user {user_id}: {e}")

    if ids_to_delete:
        try:
            collection.delete(ids=list(ids_to_delete))
            print(f"[chroma] Deleted {len(ids_to_delete)} chunks for user {user_id}")
        except Exception as e:
            print(f"[chroma] Error deleting chunks for user {user_id}: {e}")

    return deleted_sources


def get_conversation_document_sources(conversation_id: str, user_id: str = None) -> list[str]:
    """Returns a sorted list of distinct document source filenames associated with
    a conversation_id or user_id in ChromaDB."""
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



