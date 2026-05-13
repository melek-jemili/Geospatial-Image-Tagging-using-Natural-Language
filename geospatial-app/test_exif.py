# test_exif.py
import os
from src.exif_extractor import get_gps_from_exif

# Path to your images folder
images_folder = 'data/raw_images'

print("Testing EXIF GPS extraction:")
print("=" * 40)

for img_file in os.listdir(images_folder):
    if img_file.endswith('.jpg'):
        path = os.path.join(images_folder, img_file)
        lat, lon = get_gps_from_exif(path)
        
        if lat is not None and lon is not None:
            print(f"{img_file}: GPS found - Lat: {lat:.6f}, Lon: {lon:.6f}")
        else:
            print(f"{img_file}: No GPS data in EXIF")

print("\nTest complete. If no GPS data is found, your images may not have location metadata.")