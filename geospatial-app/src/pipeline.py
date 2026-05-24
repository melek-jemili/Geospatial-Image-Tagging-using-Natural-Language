import pandas as pd
import os
from .vision import VisionProcessor
from .nlp import NLPProcessorWithVision
from .embeddings import EmbeddingProcessor
from .vector_db import VectorDB
from .geospatial import GeoProcessor

class Pipeline:
    def __init__(self):
        self.vision = VisionProcessor()
        self.nlp = NLPProcessorWithVision()
        self.embeddings = EmbeddingProcessor()
        self.vector_db = VectorDB()
        self.geo = GeoProcessor()
    
    def run(self, images_df):
        results = []
        
        for idx, row in images_df.iterrows():
            # 1. Vision — supprimé, NLPProcessorWithVision intègre YOLO directement
            
            # 2. NLP → retourne un dict {tags, scores, detected_objects}
            nlp_result = self.nlp.generate_tags(row['image_path'])
            tags_list  = nlp_result["tags"]        # ✅ list[str]
            tags_text  = ", ".join(tags_list)       # ✅ str pour embed()
            
            # 3. Embeddings
            embedding = self.embeddings.embed(tags_text)
            
            # 4. Vector DB
            self.vector_db.add(
                image_id=row['image_name'],
                embedding=embedding,
                metadata={
                    'latitude':  row['latitude'],
                    'longitude': row['longitude'],
                    'tags':      tags_text,
                    'objects':   str(nlp_result["detected_objects"])
                }
            )
            
            results.append({
                'image':   row['image_name'],
                'tags':    tags_list,
                'objects': nlp_result["detected_objects"]
            })
            
            print(f"✅ {row['image_name']} → {tags_text}")
        
        # 5. Créer map
        map_obj = self.geo.create_map(images_df)
        os.makedirs('output', exist_ok=True)
        map_obj.save('output/map.html')
        
        return results