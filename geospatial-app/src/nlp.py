# src/nlp.py
from sentence_transformers import SentenceTransformer, util
import numpy as np

class NLPProcessor:
    def __init__(self):
        # Télécharge le modèle une fois (325MB)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Liste de tags possibles (extensible)
        self.tags_list = [
            # Environnement
            "urbain", "rural", "naturel", "parc", "rue",
            # Objets
            "voiture", "maison", "bâtiment", "arbre", "eau",
            # Temps
            "jour", "nuit", "nuageux", "ensoleillé",
            # Activités
            "personnes", "circulation", "calme", "animé",
            # Géographie
            "montagne", "plage", "rivière", "forêt"
        ]
    
    def generate_tags(self, image_path, detected_objects=None):
        """
        Générer tags basés sur:
        - Path image (contient indices)
        - Objets détectés (de YOLOv8)
        """
        
        # Créer description simple
        description = f"Image: {image_path}"
        if detected_objects:
            description += f" contenant: {detected_objects}"
        
        # Encoder description
        desc_embedding = self.model.encode(description)
        
        # Encoder tous les tags
        tags_embeddings = self.model.encode(self.tags_list)
        
        # Similarité cosinus
        similarities = util.pytorch_cos_sim(desc_embedding, tags_embeddings)[0]
        
        # Top 8 tags avec score
        top_k = 8
        top_indices = np.argsort(-similarities.cpu().numpy())[:top_k]
        
        tags = [self.tags_list[i] for i in top_indices]
        
        return ", ".join(tags)
    
    def add_tag(self, new_tag):
        """Ajouter un tag facilement"""
        if new_tag not in self.tags_list:
            self.tags_list.append(new_tag)