"""
validate_complete.py
Validation complète: NLP, Embeddings, ChromaDB + Comparaison QAOA vs K-means
Basé sur les VRAIS tags et les VRAIS résultats de clustering
"""

import time
import numpy as np
import pandas as pd
from sentence_transformers import util
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.cluster import KMeans
from src.vector_db import VectorDB
from src.embeddings import EmbeddingProcessor

# ============================================================
# INIT
# ============================================================

embedder = EmbeddingProcessor()
db = VectorDB()

# Charger les deux fichiers de résultats
results_df = pd.read_csv("output/results_with_clustering.csv")       # QAOA
kmeans_df  = pd.read_csv("output/results_with_clusteringkmeans.csv") # K-means

print("=" * 60)
print("VALIDATION COMPLETE - GEOSPATIAL PIPELINE")
print("=" * 60)
print(f"Dataset: {len(results_df)} images avec coordonnées GPS")

# ============================================================
# SECTION 1: VRAIS TAGS
# ============================================================

print("\n[1/5] Tags réels du pipeline:")
print("-" * 40)
print(results_df[['image_name', 'tags']].to_string(index=False))

# ============================================================
# SECTION 2: EMBEDDINGS — Vitesse + Qualité
# ============================================================

print("\n[2/5] Embeddings sur vrais tags:")
print("-" * 40)

embed_times = []
embeddings = {}

for _, row in results_df.iterrows():
    tags_text = str(row['tags'])

    start = time.time()
    emb = embedder.embed(tags_text)
    elapsed = (time.time() - start) * 1000

    embed_times.append(elapsed)
    embeddings[row['image_name']] = emb
    print(f"  {row['image_name']}: {elapsed:.1f}ms")

print(f"\nVitesse embedding:")
print(f"  Moyenne: {sum(embed_times)/len(embed_times):.1f}ms")
print(f"  Min:     {min(embed_times):.1f}ms")
print(f"  Max:     {max(embed_times):.1f}ms")

# ============================================================
# SECTION 3: SIMILARITÉ SÉMANTIQUE
# ============================================================

print("\n[3/5] Similarité sémantique:")
print("-" * 40)

print("\na) Entre vos images réelles:")
names = list(embeddings.keys())
similarities = []

for i in range(len(names)):
    for j in range(i + 1, len(names)):
        sim = util.cos_sim(embeddings[names[i]], embeddings[names[j]]).item()
        similarities.append(sim)
        print(f"  {names[i]} ↔ {names[j]}: {sim:.3f}")

print(f"\n  Similarité moyenne: {np.mean(similarities):.3f}")
print(f"  Similarité max:     {max(similarities):.3f}")
print(f"  Similarité min:     {min(similarities):.3f}")

print("\nb) Contrôle qualité (tags connus):")
all_tags     = results_df['tags'].tolist()
tag_proche_1 = str(all_tags[0])
tag_proche_2 = str(all_tags[1]) if len(all_tags) > 1 else str(all_tags[0])
tag_loin     = str(all_tags[-1]) if len(all_tags) > 2 else str(all_tags[0])

emb_proche_1 = embedder.embed(tag_proche_1)
emb_proche_2 = embedder.embed(tag_proche_2)
emb_loin     = embedder.embed(tag_loin)

sim_proche = util.cos_sim(emb_proche_1, emb_proche_2).item()
sim_loin   = util.cos_sim(emb_proche_1, emb_loin).item()

print(f"  Image 1 ↔ Image 2 (proches):  {sim_proche:.3f}  → attendu > 0.60")
print(f"  Image 1 ↔ Image N (lointain): {sim_loin:.3f}   → attendu < 0.60")

# ============================================================
# SECTION 4: CHROMADB — Insert + Query
# ============================================================

print("\n[4/5] ChromaDB - Insert + Query sur vrais tags:")
print("-" * 40)

print("\na) Insertion des vraies images:")
insert_times = []

for _, row in results_df.iterrows():
    tags_text = str(row['tags'])
    emb = embedder.embed(tags_text).tolist()
    metadata = {
        "tags": tags_text,
        "image_name": str(row['image_name'])
    }

    start = time.time()
    db.add(str(row['image_name']) + "_val", emb, metadata)
    elapsed = (time.time() - start) * 1000
    insert_times.append(elapsed)
    print(f"  Insert {row['image_name']}: {elapsed:.1f}ms")

print(f"\n  Insert total:   {sum(insert_times):.1f}ms")
print(f"  Insert moyenne: {np.mean(insert_times):.1f}ms/image")

print("\nb) Query avec tags réels:")
query_tags = str(results_df.iloc[0]['tags'])
query_emb  = embedder.embed(query_tags).tolist()

start = time.time()
search_results = db.search(query_emb, n_results=3)
query_time = (time.time() - start) * 1000

print(f"  Query: '{query_tags[:50]}...'")
print(f"  Query time: {query_time:.1f}ms")
print(f"  Top résultats: {search_results['ids'][0]}")

# ============================================================
# SECTION 5: CLUSTERING — QAOA vs K-means (deux vrais CSV)
# ============================================================

print("\n[5/5] Clustering - QAOA vs K-Means (résultats réels):")
print("-" * 40)

locations = results_df[['latitude', 'longitude']].values.astype(np.float64)

# --- QAOA ---
qaoa_labels = results_df['cluster'].values.astype(int)
n_qaoa      = len(np.unique(qaoa_labels))
qaoa_dist   = results_df['cluster'].value_counts().sort_index().tolist()

if n_qaoa > 1:
    qaoa_sil = silhouette_score(locations, qaoa_labels)
    qaoa_db  = davies_bouldin_score(locations, qaoa_labels)
else:
    qaoa_sil, qaoa_db = 0.0, 999.0

print(f"\nQAOA Quantum:")
print(f"  Clusters trouvés:      {n_qaoa}")
print(f"  Distribution:          {qaoa_dist}")
print(f"  Cluster dominant:      {max(qaoa_dist)}/{len(results_df)} ({max(qaoa_dist)/len(results_df)*100:.0f}%)")
print(f"  Silhouette score:      {qaoa_sil:.3f}  (plus proche de 1 = mieux)")
print(f"  Davies-Bouldin score:  {qaoa_db:.3f}   (plus proche de 0 = mieux)")

# --- K-means ---
kmeans_labels = kmeans_df['cluster'].values.astype(int)
n_kmeans      = len(np.unique(kmeans_labels))
kmeans_dist   = kmeans_df['cluster'].value_counts().sort_index().tolist()

if n_kmeans > 1:
    kmeans_sil = silhouette_score(locations, kmeans_labels)
    kmeans_db  = davies_bouldin_score(locations, kmeans_labels)
else:
    kmeans_sil, kmeans_db = 0.0, 999.0

print(f"\nK-Means classique:")
print(f"  Clusters trouvés:      {n_kmeans}")
print(f"  Distribution:          {kmeans_dist}")
print(f"  Cluster dominant:      {max(kmeans_dist)}/{len(kmeans_df)} ({max(kmeans_dist)/len(kmeans_df)*100:.0f}%)")
print(f"  Silhouette score:      {kmeans_sil:.3f}")
print(f"  Davies-Bouldin score:  {kmeans_db:.3f}")

# --- Comparaison ---
diff_sil = qaoa_sil - kmeans_sil
winner   = "QAOA" if diff_sil > 0 else "K-means"

print(f"\nComparaison directe:")
print(f"  Silhouette:     QAOA {qaoa_sil:.3f} vs K-means {kmeans_sil:.3f}  ({'+' if diff_sil>0 else ''}{diff_sil:.3f})")
print(f"  Davies-Bouldin: QAOA {qaoa_db:.3f} vs K-means {kmeans_db:.3f}  ({'QAOA meilleur' if qaoa_db < kmeans_db else 'K-means meilleur'})")
print(f"  Équilibre:      QAOA max={max(qaoa_dist)/len(results_df)*100:.0f}% vs K-means max={max(kmeans_dist)/len(kmeans_df)*100:.0f}%")
print(f"  Vainqueur:      {winner}")

# ============================================================
# RÉSUMÉ FINAL
# ============================================================

print("\n" + "=" * 60)
print("RÉSUMÉ POUR SLIDE VALIDATION")
print("=" * 60)
print(f"Dataset:  {len(results_df)} images | {len(results_df[results_df['latitude'].notna()])} avec GPS")
print(f"\nEmbeddings (all-MiniLM-L6-v2):")
print(f"  Dimension:       384D")
print(f"  Vitesse moyenne: {sum(embed_times)/len(embed_times):.1f}ms/image")
print(f"  Sim. proche:     {sim_proche:.3f}")
print(f"  Sim. lointain:   {sim_loin:.3f}")
print(f"\nChromaDB (PersistentClient):")
print(f"  Insert moyenne:  {np.mean(insert_times):.1f}ms/image")
print(f"  Query time:      {query_time:.1f}ms")
print(f"\nClustering (K=5 | {len(results_df)} images):")
print(f"  {'Méthode':<20} {'Silhouette':>12} {'Davies-Bouldin':>16} {'Dominant':>10}")
print(f"  {'-'*62}")
print(f"  {'K-means':<20} {kmeans_sil:>12.3f} {kmeans_db:>16.3f} {max(kmeans_dist)/len(kmeans_df)*100:>9.0f}%")
print(f"  {'QAOA Quantum':<20} {qaoa_sil:>12.3f} {qaoa_db:>16.3f} {max(qaoa_dist)/len(results_df)*100:>9.0f}%")
print(f"  Vainqueur: {winner}")
print("=" * 60)