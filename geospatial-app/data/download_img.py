#!/usr/bin/env python3
"""
Script pour télécharger les images depuis le CSV
Utilisation: python download_images.py
"""

import pandas as pd
import requests
from pathlib import Path
import time

# Charger le CSV
df = pd.read_csv('images_metadata.csv')

# Créer dossier
data_dir = Path('data/raw_images')
data_dir.mkdir(parents=True, exist_ok=True)

print(f"📥 Téléchargement de {len(df)} images...\n")

for idx, row in df.iterrows():
    image_name = row['image_name']
    url = row['download_url']
    description = row['description']
    
    # Chemin fichier
    file_path = data_dir / f"{image_name}.jpg"
    
    try:
        print(f"[{idx+1}/{len(df)}] 📷 Téléchargement: {image_name}")
        print(f"    └─ {description}")
        
        # Télécharger
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Sauvegarder
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"     Sauvegardé: {file_path}\n")
        
        time.sleep(1)  # Respecter les serveurs
        
    except Exception as e:
        print(f"     Erreur: {e}\n")

# Créer metadata.csv pour le projet
print("\n" + "="*50)
print(" Création du CSV pour le projet...")

# Garder seulement les colonnes nécessaires
metadata_for_project = df[['image_name', 'latitude', 'longitude', 'description']].copy()

# Sauvegarder
metadata_for_project.to_csv('data/metadata.csv', index=False)

print(f"Fichier créé: data/metadata.csv")
print(f"Images dans: data/raw_images/")
print(f"\nPrêt à utiliser!")