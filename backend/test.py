# one-off, in a python shell or temp debug endpoint
from ingestion.chroma_client import cache_collection
cache_collection.delete(ids=cache_collection.get()['ids'])