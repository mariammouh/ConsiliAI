from ingestion.chroma_client import analysis_cache_collection,cache_collection
analysis_cache_collection.delete(ids=analysis_cache_collection.get()['ids'])
cache_collection.delete(ids=cache_collection.get()['ids'])
