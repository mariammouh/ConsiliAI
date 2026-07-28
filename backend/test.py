from ingestion.chroma_client import cache_collection

data = cache_collection.get(
    include=["documents", "metadatas"]
)

for i, (doc, meta) in enumerate(zip(data["documents"], data["metadatas"])):
    print("=" * 80)
    print(f"Document #{i}")
    print("Metadata:", meta)
    print("-" * 80)
    print(doc)
    print()