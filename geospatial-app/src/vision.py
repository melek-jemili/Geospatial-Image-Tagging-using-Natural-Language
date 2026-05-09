from ultralytics import YOLO
from PIL import Image

class VisionProcessor:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")
    
    def detect(self, image_path):
        results = self.model(image_path)
        return results[0].boxes.data.cpu().numpy()