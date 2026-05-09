import pandas as pd
import os
from dotenv import load_dotenv
from src.pipeline import Pipeline

load_dotenv()

# Charger données
images_df = pd.read_csv('data/metadata.csv')
images_df['image_path'] = images_df['image_name'].apply(lambda x: f"data/raw_images/{x}.jpg")

# Lancer pipeline
pipeline = Pipeline()
results = pipeline.run(images_df)

print("\n TERMINÉ!")
print(f"Résultats: {len(results)} images traitées")
print("Carte: output/map.html")