"""
Main pipeline: Classique + Quantum Clustering
"""

import pandas as pd
import os
import logging
from dotenv import load_dotenv
from src.pipeline import Pipeline
from src.exif_extractor import get_gps
from src.quantum_spatial_optimizer import QuantumSpatialOptimizer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("="*60)
logger.info("SPATIAL GEOREFERENCING + QUANTUM CLUSTERING")
logger.info("="*60)

# ============================================================
# PHASE 1: EXIF EXTRACTION & METADATA
# ============================================================

logger.info("\n[1/3] Extracting EXIF data...")

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
logger.info(f"Found {len(images_df)} images with EXIF")

# Load CSV for fallback
csv_df = pd.read_csv('data/metadata.csv')
csv_df['image_path'] = csv_df['image_name'].apply(lambda x: f"data/raw_images/{x}.jpg")

# Merge
merged_df = pd.merge(
    images_df, 
    csv_df[['image_name', 'latitude', 'longitude']], 
    on='image_name', 
    how='left', 
    suffixes=('_exif', '_csv')
)
merged_df['latitude'] = merged_df['latitude_exif'].fillna(merged_df['latitude_csv'])
merged_df['longitude'] = merged_df['longitude_exif'].fillna(merged_df['longitude_csv'])

images_df = merged_df.dropna(subset=['latitude', 'longitude'])[
    ['image_name', 'latitude', 'longitude', 'image_path']
]

logger.info(f"After merge: {len(images_df)} images with valid coordinates")

# ============================================================
# PHASE 2: CLASSICAL PIPELINE
# ============================================================

logger.info("\n[2/3] Running classical pipeline...")

pipeline = Pipeline()
results = pipeline.run(images_df)

# ✅ CONVERSION
if isinstance(results, list):
    logger.info("Converting list to DataFrame...")
    results_df = pd.DataFrame(results)
elif isinstance(results, dict):
    logger.info("Converting dict to DataFrame...")
    results_df = pd.DataFrame([results])
else:
    results_df = results

logger.info(f"Pipeline returned: {results_df.columns.tolist()}")

# ✅ MERGER AVEC COORDONNÉES GPS (CRUCIAL!)
logger.info("Merging with GPS coordinates...")

# Renommer 'image' → 'image_name' si nécessaire
if 'image' in results_df.columns and 'image_name' not in results_df.columns:
    results_df.rename(columns={'image': 'image_name'}, inplace=True)

# Merger sur image_name
results_df = pd.merge(
    images_df[['image_name', 'latitude', 'longitude', 'image_path']],
    results_df,
    on='image_name',
    how='inner'
)

logger.info(f"Final columns: {results_df.columns.tolist()}")
logger.info(f"Final shape: {results_df.shape}")

# Vérifier colonnes nécessaires
required_cols = ['latitude', 'longitude', 'image_name']
missing = [col for col in required_cols if col not in results_df.columns]
if missing:
    logger.error(f"Missing: {missing}")
    exit(1)

logger.info(f"Classical pipeline complete: {len(results_df)} images")

# ============================================================
# PHASE 3: QUANTUM SPATIAL CLUSTERING
# ============================================================

logger.info("\n[3/3] Quantum spatial optimization...")

USE_QUANTUM_CLUSTERING = os.getenv("USE_QUANTUM_CLUSTERING", "true").lower() == "true"
USE_IBM_QUANTUM = os.getenv("USE_IBM_QUANTUM", "false").lower() == "true"
NUM_CLUSTERS = int(os.getenv("NUM_CLUSTERS", "5"))

if USE_QUANTUM_CLUSTERING:
    logger.info(f"Initializing quantum optimizer (IBM={USE_IBM_QUANTUM})...")
    
    try:
        quantum_opt = QuantumSpatialOptimizer(use_ibm=USE_IBM_QUANTUM)
        locations = results_df[['latitude', 'longitude']].values
        
        logger.info(f"Optimizing {len(locations)} images into {NUM_CLUSTERS} clusters...")
        cluster_assignments, metrics = quantum_opt.optimize_clustering(
            locations, 
            num_clusters=NUM_CLUSTERS
        )
        
        results_df['cluster'] = cluster_assignments
        
        logger.info("Clustering metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                logger.info(f"  {key}: {value:.4f}")
            else:
                logger.info(f"  {key}: {value}")
    
    except Exception as e:
        logger.error(f"Quantum clustering failed: {e}")
        logger.warning("Falling back to classical K-means...")
        
        from sklearn.cluster import KMeans
        
        locations = results_df[['latitude', 'longitude']].values
        kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42)
        results_df['cluster'] = kmeans.fit_predict(locations)

else:
    logger.info("Using classical K-means...")
    from sklearn.cluster import KMeans
    
    locations = results_df[['latitude', 'longitude']].values
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42)
    results_df['cluster'] = kmeans.fit_predict(locations)

# ============================================================
# PHASE 4: VISUALIZATION
# ============================================================

logger.info("\nGenerating visualizations...")

from src.geospatial import GeoProcessor

geo_processor = GeoProcessor()
map_obj = geo_processor.create_map_with_clusters(results_df)
map_obj.save('output/map_with_clustering.html')

results_df.to_csv('output/results_with_clustering.csv', index=False)
results_df.to_json('output/results_with_clustering.json', orient='records')

# ============================================================
# RÉSULTATS
# ============================================================

logger.info("\n" + "="*60)
logger.info("PIPELINE COMPLETE!")
logger.info("="*60)
logger.info(f"Total images: {len(results_df)}")
logger.info(f"Clusters: {results_df['cluster'].nunique()}")
logger.info(f"\nOutputs:")
logger.info(f"  Map: output/map_with_clustering.html")
logger.info(f"  CSV: output/results_with_clustering.csv")
logger.info(f"  JSON: output/results_with_clustering.json")

logger.info("\nCluster distribution:")
for cid in sorted(results_df['cluster'].unique()):
    count = len(results_df[results_df['cluster'] == cid])
    logger.info(f"  Cluster {cid}: {count} images")

logger.info("="*60)