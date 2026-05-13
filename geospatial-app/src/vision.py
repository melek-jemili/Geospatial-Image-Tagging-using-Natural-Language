from ultralytics import YOLO
from PIL import Image

class VisionProcessor:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")
    
    def detect(self, image_path):
        results = self.model(image_path)
        # Get detected class names
        detected_classes = []
        if len(results[0].boxes) > 0:
            class_indices = results[0].boxes.cls.cpu().numpy().astype(int)
            for idx in class_indices:
                detected_classes.append(results[0].names[idx])
        return detected_classes