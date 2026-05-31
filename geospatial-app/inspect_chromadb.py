# inspect_chromadb.py
import chromadb
from chromadb.config import Settings

# Connect to your ChromaDB (adjust path if needed)
client = chromadb.PersistentClient(path="./chroma_db")  # Assuming default path from vector_db.py

# Get the collection (assuming it's named 'images' or check vector_db.py)
collection = client.get_collection("images")  # Replace with your collection name

# Get all stored data
results = collection.get(include=['metadatas', 'documents', 'embeddings'])

print("ChromaDB Collection Contents:")
print("=" * 50)
print(f"Total items: {len(results['ids'])}")

for i, id in enumerate(results['ids']):
    print(f"\nItem {i+1}:")
    print(f"  ID: {id}")
    print(f"  Metadata: {results['metadatas'][i]}")
    print(f"  Document: {results.get('documents', [None])[i]}")
    # Embeddings are vectors (long), so just show length
    if results.get('embeddings') is not None:
        print(f"  Embedding length: {len(results['embeddings'][i])}")

# Optional: Query for similar items (example)
# query_results = collection.query(query_embeddings=[[0.1]*384], n_results=2)  # Random vector
# print("\nQuery Results:", query_results)