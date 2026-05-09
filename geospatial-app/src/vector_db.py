import chromadb

class VectorDB:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("images")
    
    def add(self, image_id, embedding, metadata):
        self.collection.add(
            ids=[image_id],
            embeddings=[embedding],
            metadatas=[metadata]
        )
    
    def search(self, query_embedding, n_results=10):
        return self.collection.query(query_embeddings=[query_embedding], n_results=n_results)