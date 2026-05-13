from sentence_transformers import SentenceTransformer, util
from ultralytics import YOLO
import numpy as np
import os

class NLPProcessorWithVision:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.yolo = YOLO("yolov8n.pt")  # Vision intégrée
        
        self.tags_by_category = {
            "environnement": ["urbain", "rural", "naturel", "parc", "rue"],
            "objets": ["voiture", "maison", "bâtiment", "arbre", "eau"],
            "temporel": ["jour", "nuit", "nuageux", "ensoleillé"],
            "activité": ["personnes", "circulation", "calme", "animé"],
            "géographie": ["montagne", "plage", "rivière", "forêt"],
            "saison": ["printemps", "été", "automne", "hiver"],
            "qualité": ["net", "flou", "bien_éclairé", "sombre"]
        }
        
        self.tags_list = []
        for tags in self.tags_by_category.values():
            self.tags_list.extend(tags)
        
        self.tags_embeddings = self.model.encode(self.tags_list)
        
        # Mapping YOLO classes -> tags
        self.yolo_to_tags = {
            "person": "personnes",
            "car": "voiture",
            "truck": "voiture",
            "bus": "circulation",
            "house": "maison",
            "building": "bâtiment",
            "tree": "arbre",
            "mountain": "montagne",
            "water": "eau",
            "sky": "jour" if "hour" > 6 else "nuit"
        }
    
    def extract_objects_from_image(self, image_path):
        """Détecter objets avec YOLO"""
        results = self.yolo(image_path)
        
        detected_objects = []
        for r in results:
            for c in r.boxes.cls:
                class_name = self.yolo.names[int(c)]
                detected_objects.append(class_name)
        
        return detected_objects
    
    def generate_tags(self, image_path, latitude=None, longitude=None, description=None):
        """Générer tags avec vision automatique"""
        
        # 1. Détecter objets avec YOLO
        detected_objects = self.extract_objects_from_image(image_path)
        
        # 2. Mapper vers tags
        mapped_tags = []
        for obj in detected_objects:
            if obj in self.yolo_to_tags:
                mapped_tags.append(self.yolo_to_tags[obj])
        
        # 3. Créer description enrichie
        context_parts = []
        if description:
            context_parts.append(description)
        if mapped_tags:
            context_parts.append(f"contient: {', '.join(set(mapped_tags))}")
        
        description_text = " ".join(context_parts) if context_parts else "image"
        
        # 4. Score avec embeddings
        desc_embedding = self.model.encode(description_text)
        similarities = util.pytorch_cos_sim(desc_embedding, self.tags_embeddings)[0]
        similarities = similarities.cpu().numpy()
        
        # 5. Retourner résultats
        top_indices = np.argsort(-similarities)[:10]
        
        results = {
            "tags": [self.tags_list[i] for i in top_indices],
            "scores": [float(similarities[i]) for i in top_indices],
            "detected_objects": detected_objects
        }
        
        return results