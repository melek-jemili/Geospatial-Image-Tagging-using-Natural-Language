import pandas as pd
from .vision import VisionProcessor
from .nlp import NLPProcessor
from .embeddings import EmbeddingProcessor
from .vector_db import VectorDB
from .geospatial import GeoProcessor

class Pipeline:
    def __init__(self):
        self.vision = VisionProcessor()
        self.nlp = NLPProcessor()
        self.embeddings = EmbeddingProcessor()
        self.vector_db = VectorDB()
        self.geo = GeoProcessor()
    
    def run(self, images_df):
        results = []
        
        for idx, row in images_df.iterrows():
            # 1. Vision
            objects = self.vision.detect(row['image_path'])
            
            # 2. NLP
            tags = self.nlp.generate_tags(row['image_path'], row['latitude'], row['longitude'])
            
            # 3. Embeddings
            embedding = self.embeddings.embed(tags)
            
            # 4. Vector DB
            self.vector_db.add(
                image_id=row['image_name'],
                embedding=embedding,
                metadata={
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'tags': tags,
                    'objects': str(objects)
                }
            )
            
            results.append({
                'image': row['image_name'],
                'tags': tags,
                'objects': objects
            })
            
            print(f"{row['image_name']}")
        
        # 5. Créer map
        map_obj = self.geo.create_map(images_df)
        map_obj.save('output/map.html')
        
        return results