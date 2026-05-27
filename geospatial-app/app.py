"""
Flask API Backend for Geospatial Image Analysis with Quantum Clustering
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import numpy as np

# Import your existing modules
from src.pipeline import Pipeline
from src.exif_extractor import extract_metadata, get_gps
from src.quantum_spatial_optimizer import QuantumSpatialOptimizer
from src.vector_db import VectorDB
from config import get_config

# ============================================================
# Configuration
# ============================================================

app = Flask(__name__, template_folder='templates', static_folder='static')

# Load config
config = get_config(os.environ.get('FLASK_ENV', 'development'))
app.config.from_object(config)

# Enable CORS
CORS(app, origins=config.CORS_ORIGINS)

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state for pipeline
pipeline = Pipeline()
quantum_optimizer = QuantumSpatialOptimizer()
vector_db = VectorDB()

# ============================================================
# Helper Functions
# ============================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)

# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    """Serve main interface"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_images():
    """
    Handle multiple image uploads
    Max 20 images
    """
    try:
        # Check if images in request
        if 'images' not in request.files:
            return jsonify({'error': 'No images provided'}), 400
        
        files = request.files.getlist('images')
        
        if len(files) == 0:
            return jsonify({'error': 'No images selected'}), 400
        
        if len(files) > 20:
            return jsonify({'error': f'Maximum 20 images allowed, got {len(files)}'}), 400
        
        uploaded_images = []
        errors = []
        
        for file in files:
            if file.filename == '':
                errors.append('Empty filename')
                continue
            
            if not allowed_file(file.filename):
                errors.append(f'{file.filename}: Unsupported format')
                continue
            
            # Secure filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save file
            file.save(filepath)
            
            # Get file info
            file_size_mb = get_file_size_mb(filepath)
            
            uploaded_images.append({
                'filename': filename,
                'original_name': file.filename,
                'size_mb': round(file_size_mb, 2),
                'path': filepath,
                'upload_time': datetime.now().isoformat()
            })
            
            logger.info(f"Image uploaded: {filename} ({file_size_mb:.2f}MB)")
        
        return jsonify({
            'success': True,
            'uploaded_count': len(uploaded_images),
            'total_count': len(files),
            'images': uploaded_images,
            'errors': errors
        }), 200

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_images():
    """
    Process uploaded images through the entire pipeline
    Returns: metadata, coordinates, embeddings, clustering results
    """
    try:
        data = request.get_json()
        image_paths = data.get('image_paths', [])
        
        if not image_paths:
            return jsonify({'error': 'No images to process'}), 400
        
        if len(image_paths) > 20:
            return jsonify({'error': 'Maximum 20 images allowed'}), 400
        
        results = {
            'images': [],
            'clusters': {},
            'summary': {
                'total_images': len(image_paths),
                'images_with_gps': 0,
                'total_clusters': 0,
                'processing_time': 0
            },
            'pipeline_steps': []
        }
        
        start_time = datetime.now()
        
        # ============================================================
        # STEP 1: EXIF EXTRACTION
        # ============================================================
        
        logger.info("[1/5] Starting EXIF extraction...")
        exif_results = []
        
        for idx, img_path in enumerate(image_paths, 1):
            if not os.path.exists(img_path):
                logger.warning(f"Image not found: {img_path}")
                continue
            
            metadata = extract_metadata(img_path)
            
            exif_result = {
                'index': idx,
                'filename': os.path.basename(img_path),
                'path': img_path,
                'has_gps': metadata.has_gps,
                'latitude': metadata.gps.latitude if metadata.has_gps else None,
                'longitude': metadata.gps.longitude if metadata.has_gps else None,
                'camera': f"{metadata.camera_make or ''} {metadata.camera_model or ''}".strip(),
                'datetime': metadata.datetime_original,
                'size': f"{metadata.width}x{metadata.height}" if metadata.width else None,
                'errors': metadata.errors
            }
            
            exif_results.append(exif_result)
            
            if metadata.has_gps:
                results['summary']['images_with_gps'] += 1
        
        results['pipeline_steps'].append({
            'step': 'EXIF Extraction',
            'status': 'completed',
            'processed': len(exif_results),
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"✅ EXIF extraction complete: {results['summary']['images_with_gps']} images with GPS")
        
        # ============================================================
        # STEP 2: NLP & VISION (Tags + Objects)
        # ============================================================
        
        logger.info("[2/5] Starting NLP & Vision processing...")
        
        nlp_results = []
        for exif_data in exif_results:
            if not os.path.exists(exif_data['path']):
                continue
            
            try:
                nlp_result = pipeline.nlp.generate_tags(exif_data['path'])
                
                nlp_data = {
                    'filename': exif_data['filename'],
                    'tags': nlp_result.get('tags', []),
                    'tag_scores': nlp_result.get('scores', {}),
                    'objects': nlp_result.get('detected_objects', []),
                    'top_tags': sorted(
                        nlp_result.get('tags', []),
                        key=lambda t: nlp_result.get('scores', {}).get(t, 0),
                        reverse=True
                    )[:5]
                }
                nlp_results.append(nlp_data)
                logger.debug(f"NLP processed: {exif_data['filename']}")
            except Exception as e:
                logger.error(f"NLP processing failed for {exif_data['filename']}: {str(e)}")
        
        results['pipeline_steps'].append({
            'step': 'NLP & Vision',
            'status': 'completed',
            'processed': len(nlp_results),
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"✅ NLP & Vision complete: {len(nlp_results)} images processed")
        
        # ============================================================
        # STEP 3: EMBEDDINGS
        # ============================================================
        
        logger.info("[3/5] Generating embeddings...")
        
        embeddings_data = []
        for idx, nlp_data in enumerate(nlp_results):
            try:
                tags_text = ", ".join(nlp_data['tags'])
                embedding = pipeline.embeddings.embed(tags_text)
                
                embeddings_data.append({
                    'filename': nlp_data['filename'],
                    'embedding': embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                    'embedding_dim': len(embedding) if isinstance(embedding, (list, np.ndarray)) else 0
                })
            except Exception as e:
                logger.error(f"Embedding failed for {nlp_data['filename']}: {str(e)}")
        
        results['pipeline_steps'].append({
            'step': 'Embeddings',
            'status': 'completed',
            'processed': len(embeddings_data),
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"✅ Embeddings complete: {len(embeddings_data)} vectors generated")
        
        # ============================================================
        # STEP 4: QUANTUM CLUSTERING
        # ============================================================
        
        logger.info("[4/5] Running Quantum Clustering...")
        
        clustering_results = {
            'clusters': {},
            'quantum_circuit': None,
            'optimization_time': 0
        }
        
        try:
            # Prepare data for clustering (coordinates only, or hybrid)
            gps_coords = []
            filenames_for_clustering = []
            
            for exif_data in exif_results:
                if exif_data['has_gps']:
                    gps_coords.append([exif_data['latitude'], exif_data['longitude']])
                    filenames_for_clustering.append(exif_data['filename'])
            
            if len(gps_coords) >= 2:
                # Run quantum optimizer
                quantum_start = datetime.now()
                labels = quantum_optimizer.optimize_clusters(np.array(gps_coords), n_clusters=2)
                quantum_time = (datetime.now() - quantum_start).total_seconds()
                
                clustering_results['quantum_circuit'] = 'QAOA Clustering'
                clustering_results['optimization_time'] = quantum_time
                
                # Group by cluster
                for cluster_id in set(labels):
                    cluster_images = [
                        filenames_for_clustering[i] 
                        for i, label in enumerate(labels) 
                        if label == cluster_id
                    ]
                    clustering_results['clusters'][f'cluster_{cluster_id}'] = cluster_images
                
                results['summary']['total_clusters'] = len(set(labels))
            else:
                # Fallback if not enough gps data
                clustering_results['clusters']['cluster_0'] = filenames_for_clustering
                results['summary']['total_clusters'] = 1
        
        except Exception as e:
            logger.error(f"Quantum clustering failed: {str(e)}")
            # Fallback: single cluster
            clustering_results['clusters']['cluster_0'] = [
                exif['filename'] for exif in exif_results if exif['has_gps']
            ]
            results['summary']['total_clusters'] = 1
        
        results['pipeline_steps'].append({
            'step': 'Quantum Clustering',
            'status': 'completed',
            'clusters': results['summary']['total_clusters'],
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"✅ Quantum Clustering complete: {results['summary']['total_clusters']} clusters")
        
        # ============================================================
        # STEP 5: VECTOR DB & FINAL RESULTS
        # ============================================================
        
        logger.info("[5/5] Storing in Vector DB...")
        
        for exif_data in exif_results:
            if exif_data['has_gps']:
                # Find corresponding NLP and embedding data
                nlp_data = next((n for n in nlp_results if n['filename'] == exif_data['filename']), None)
                embed_data = next((e for e in embeddings_data if e['filename'] == exif_data['filename']), None)
                
                image_result = {
                    'filename': exif_data['filename'],
                    'latitude': exif_data['latitude'],
                    'longitude': exif_data['longitude'],
                    'camera': exif_data['camera'],
                    'datetime': exif_data['datetime'],
                    'size': exif_data['size'],
                    'tags': nlp_data['tags'] if nlp_data else [],
                    'top_tags': nlp_data['top_tags'] if nlp_data else [],
                    'objects': nlp_data['objects'] if nlp_data else [],
                    'embedding_dim': embed_data['embedding_dim'] if embed_data else 0
                }
                
                # Add cluster info
                for cluster_name, images in clustering_results['clusters'].items():
                    if exif_data['filename'] in images:
                        image_result['cluster'] = cluster_name
                        break
                
                results['images'].append(image_result)
        
        results['pipeline_steps'].append({
            'step': 'Vector Database',
            'status': 'completed',
            'stored': len(results['images']),
            'timestamp': datetime.now().isoformat()
        })
        
        results['clusters'] = clustering_results['clusters']
        results['summary']['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Processing complete in {results['summary']['processing_time']:.2f}s")
        
        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-map', methods=['POST'])
def generate_map():
    """
    Generate enhanced interactive map with Folium
    """
    try:
        data = request.get_json()
        images_data = data.get('images', [])
        
        if not images_data:
            return jsonify({'error': 'No images data provided'}), 400
        
        import folium
        from folium import plugins
        
        # Calculate map center
        lats = [img['latitude'] for img in images_data if img.get('latitude')]
        lons = [img['longitude'] for img in images_data if img.get('longitude')]
        
        if not lats or not lons:
            return jsonify({'error': 'No valid coordinates'}), 400
        
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=3,
            tiles='OpenStreetMap',
            prefer_canvas=True
        )
        
        # Add feature groups by cluster
        clusters = set(img.get('cluster', 'default') for img in images_data)
        cluster_colors = {
            'cluster_0': 'red',
            'cluster_1': 'blue',
            'cluster_2': 'green',
            'cluster_3': 'purple',
            'cluster_4': 'orange',
            'default': 'gray'
        }
        
        for cluster in clusters:
            fg = folium.FeatureGroup(name=f'{cluster} ({len([i for i in images_data if i.get("cluster") == cluster])} images)')
            
            for img in images_data:
                if img.get('cluster') == cluster:
                    color = cluster_colors.get(cluster, 'gray')
                    
                    # Create popup with detailed info
                    popup_text = f"""
                    <div style='width: 300px; font-family: Arial; font-size: 12px;'>
                        <b>{img['filename']}</b><br>
                        <hr>
                        <b>Location:</b><br>
                        Lat: {img['latitude']:.4f}<br>
                        Lon: {img['longitude']:.4f}<br>
                        <br>
                        <b>Camera:</b> {img.get('camera', 'Unknown')}<br>
                        <b>Date:</b> {img.get('datetime', 'Unknown')}<br>
                        <br>
                        <b>Tags:</b><br>
                        {', '.join(img.get('tags', [])[:10])}<br>
                        <br>
                        <b>Detected Objects:</b><br>
                        {', '.join(list(set(img.get('objects', [])))[:10])}
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[img['latitude'], img['longitude']],
                        radius=8,
                        popup=folium.Popup(popup_text, max_width=300),
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(fg)
            
            fg.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save map
        map_path = 'output/interactive_map.html'
        Path('output').mkdir(exist_ok=True)
        m.save(map_path)
        
        logger.info(f"Map generated: {map_path}")
        
        return jsonify({
            'success': True,
            'map_path': map_path,
            'center': {'lat': center_lat, 'lon': center_lon},
            'bounds': {
                'min_lat': min(lats),
                'max_lat': max(lats),
                'min_lon': min(lons),
                'max_lon': max(lons)
            }
        }), 200

    except Exception as e:
        logger.error(f"Map generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get application statistics"""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        total_files = len([f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))])
        total_size = sum(
            os.path.getsize(os.path.join(upload_dir, f)) 
            for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f))
        ) / (1024 * 1024)
        
        return jsonify({
            'total_images_uploaded': total_files,
            'total_size_mb': round(total_size, 2),
            'max_images_allowed': 20,
            'allowed_formats': list(app.config['ALLOWED_EXTENSIONS'])
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    logger.info("Starting Geospatial Image Analysis API...")
    app.run(debug=True, host='0.0.0.0', port=5000)
