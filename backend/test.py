from ingestion.chroma_client import analysis_cache_collection,search_cache_collection
analysis_cache_collection.delete(ids=analysis_cache_collection.get()['ids'])
search_cache_collection.delete(ids=search_cache_collection.get()['ids'])
