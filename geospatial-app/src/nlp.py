from sentence_transformers import SentenceTransformer, util
from ultralytics import YOLO
from datetime import datetime
import numpy as np

class NLPProcessorWithVision:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.yolo = YOLO("yolov8n.pt")
        
        self.tags_by_category = {
            "environnement": ["urbain", "rural", "naturel", "parc", "rue"],
            "objets":        ["voiture", "maison", "bâtiment", "arbre", "eau"],
            "temporel":      ["jour", "nuit", "nuageux", "ensoleillé"],
            "activité":      ["personnes", "circulation", "calme", "animé"],
            "géographie":    ["montagne", "plage", "rivière", "forêt"],
            "saison":        ["printemps", "été", "automne", "hiver"],
            "qualité":       ["net", "flou", "bien_éclairé", "sombre"]
        }
        
        self.tags_list = [t for tags in self.tags_by_category.values() for t in tags]
        self.tags_embeddings = self.model.encode(self.tags_list)
        
        # ✅ "sky" → None, résolu dynamiquement
        self.yolo_to_tags = {
            "person":   "personnes",
            "car":      "voiture",
            "truck":    "voiture",
            "bus":      "circulation",
            "house":    "maison",
            "building": "bâtiment",
            "tree":     "arbre",
            "mountain": "montagne",
            "water":    "eau",
            "sky":      None,
        }

    def _resolve_sky_tag(self, hour: int | None = None) -> str:
        if hour is None:
            hour = datetime.now().hour
        return "jour" if 6 <= hour < 21 else "nuit"

    def get_yolo_tags(self, hour: int | None = None) -> dict:
        return {**self.yolo_to_tags, "sky": self._resolve_sky_tag(hour)}

    def extract_objects_from_image(self, image_path):
        results = self.yolo(image_path)
        detected_objects = []
        for r in results:
            for c in r.boxes.cls:
                detected_objects.append(self.yolo.names[int(c)])
        return detected_objects

    def generate_tags(self, image_path, latitude=None, longitude=None, description=None, hour: int | None = None):
        yolo_tags = self.get_yolo_tags(hour)
        detected_objects = self.extract_objects_from_image(image_path)
        mapped_tags = [yolo_tags[obj] for obj in detected_objects if obj in yolo_tags]

        context_parts = []
        if description:
            context_parts.append(description)
        if mapped_tags:
            context_parts.append(f"contient: {', '.join(set(mapped_tags))}")

        # ✅ fallback : nom du fichier au lieu de "image"
        if not context_parts:
            from pathlib import Path
            context_parts.append(Path(image_path).stem.replace("_", " "))

        description_text = " ".join(context_parts)

        desc_embedding = self.model.encode(description_text)
        similarities = util.pytorch_cos_sim(desc_embedding, self.tags_embeddings)[0]
        similarities = similarities.cpu().numpy()
        top_indices = np.argsort(-similarities)[:10]

        return {
            "tags":             [self.tags_list[i] for i in top_indices],
            "scores":           [float(similarities[i]) for i in top_indices],
            "detected_objects": detected_objects
        }