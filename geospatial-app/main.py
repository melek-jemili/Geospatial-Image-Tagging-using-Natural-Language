import pandas as pd
import os
from dotenv import load_dotenv
from src.pipeline import Pipeline
from src.exif_extractor import get_gps
load_dotenv()

# Scan images and build dataframe from EXIF
images_data = []
for img_file in os.listdir('data/raw_images'):
    if img_file.endswith('.jpg'):
        path = f"data/raw_images/{img_file}"
        lat, lon = get_gps(path)
        images_data.append({
            'image_name': img_file.replace('.jpg', ''),
            'latitude': lat,
            'longitude': lon,
            'image_path': path
        })

images_df = pd.DataFrame(images_data)

# Load CSV for fallback coordinates
csv_df = pd.read_csv('data/metadata.csv')
csv_df['image_path'] = csv_df['image_name'].apply(lambda x: f"data/raw_images/{x}.jpg")

# Merge: Use EXIF if available, else CSV
merged_df = pd.merge(images_df, csv_df[['image_name', 'latitude', 'longitude']], on='image_name', how='left', suffixes=('_exif', '_csv'))
merged_df['latitude'] = merged_df['latitude_exif'].fillna(merged_df['latitude_csv'])
merged_df['longitude'] = merged_df['longitude_exif'].fillna(merged_df['longitude_csv'])

# Filter to images with valid coordinates
images_df = merged_df.dropna(subset=['latitude', 'longitude'])[['image_name', 'latitude', 'longitude', 'image_path']]

# Lancer pipeline
pipeline = Pipeline()
results = pipeline.run(images_df)

print("\n TERMINÉ!")
print(f"Résultats: {len(results)} images traitées")
print("Carte: output/map.html")