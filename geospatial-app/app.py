"""
Flask Application - Spatial Georeferencing with Quantum Clustering
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Import pipeline modules
from src.pipeline import Pipeline
from src.exif_extractor import get_gps
from src.quantum_spatial_optimizer import QuantumSpatialOptimizer
from src.geospatial import GeoProcessor

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration
UPLOAD_FOLDER = 'data/raw_images'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'tiff', 'heic', 'gif', 'bmp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES = 20

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create folders
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

# Enable CORS
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize pipeline
pipeline = Pipeline()
quantum_optimizer = QuantumSpatialOptimizer()
geo_processor = GeoProcessor()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath):
    """Get file size in MB"""
    return os.path.getsize(filepath) / (1024 * 1024)

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/api/upload', methods=['POST'])
def upload_images():
    """
    Handle image uploads
    """
    try:
        if 'images' not in request.files:
            return jsonify({'error': 'No images provided'}), 400
        
        files = request.files.getlist('images')
        
        if len(files) == 0:
            return jsonify({'error': 'No images selected'}), 400
        
        if len(files) > MAX_FILES:
            return jsonify({'error': f'Maximum {MAX_FILES} images allowed'}), 400
        
        uploaded = []
        errors = []
        
        for file in files:
            if file.filename == '':
                errors.append('Empty filename')
                continue
            
            if not allowed_file(file.filename):
                errors.append(f'{file.filename}: Format not supported')
                continue
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save file
            file.save(filepath)
            file_size = get_file_size_mb(filepath)
            
            uploaded.append({
                'filename': filename,
                'original_name': file.filename,
                'path': filepath,
                'size_mb': round(file_size, 2)
            })
            
            logger.info(f"✅ Uploaded: {filename} ({file_size:.2f}MB)")
        
        return jsonify({
            'success': True,
            'uploaded': len(uploaded),
            'total': len(files),
            'images': uploaded,
            'errors': errors
        }), 200

    except Exception as e:
        logger.error(f"❌ Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_images():
    """
    Process images through full pipeline
    """
    try:
        data = request.get_json()
        image_paths = data.get('image_paths', [])
        
        if not image_paths:
            return jsonify({'error': 'No images to process'}), 400
        
        logger.info(f"📊 Processing {len(image_paths)} images...")
        
        # Extract EXIF and create DataFrame
        images_data = []
        for img_path in image_paths:
            if os.path.exists(img_path):
                lat, lon = get_gps(img_path)
                images_data.append({
                    'image_name': os.path.basename(img_path).replace('.jpg', ''),
                    'latitude': lat,
                    'longitude': lon,
                    'image_path': img_path
                })
        
        images_df = pd.DataFrame(images_data)
        
        # Filter valid coordinates
        images_df = images_df.dropna(subset=['latitude', 'longitude'])
        
        logger.info(f"✅ Found {len(images_df)} images with GPS coordinates")
        
        if len(images_df) == 0:
            return jsonify({'error': 'No valid coordinates found'}), 400
        
        # Run pipeline
        logger.info("🔄 Running classical pipeline...")
        results_list = pipeline.run(images_df)
        
        # Convert results list to DataFrame
        results_df = pd.DataFrame(results_list)
        
        # Merge with GPS
        results_df = pd.merge(
            images_df[['image_name', 'latitude', 'longitude', 'image_path']],
            results_df,
            left_on='image_name',
            right_on='image',
            how='inner'
        )
        
        logger.info(f"✅ Pipeline complete: {len(results_df)} images processed")
        
        # Quantum Clustering
        logger.info("⚛️  Running quantum clustering...")
        USE_QUANTUM = os.getenv('USE_QUANTUM_CLUSTERING', 'true').lower() == 'true'
        
        # Adaptive number of clusters (cannot exceed number of samples)
        num_clusters = min(5, len(results_df))
        
        if len(results_df) == 1:
            # Single image - assign to cluster 0
            results_df['cluster'] = 0
            logger.info("✅ Single image: assigned to cluster 0")
        elif USE_QUANTUM and len(results_df) >= 2:
            try:
                locations = results_df[['latitude', 'longitude']].values.astype(np.float64)
                assignments, metrics = quantum_optimizer.optimize_clustering(locations, num_clusters=num_clusters)
                results_df['cluster'] = assignments
                logger.info(f"✅ Quantum clustering: {len(np.unique(assignments))} clusters found")
            except Exception as e:
                logger.warning(f"⚠️  Quantum clustering failed, using K-means: {e}")
                from sklearn.cluster import KMeans
                locations = results_df[['latitude', 'longitude']].values
                kmeans = KMeans(n_clusters=num_clusters, random_state=42)
                results_df['cluster'] = kmeans.fit_predict(locations)
        else:
            from sklearn.cluster import KMeans
            locations = results_df[['latitude', 'longitude']].values
            kmeans = KMeans(n_clusters=num_clusters, random_state=42)
            results_df['cluster'] = kmeans.fit_predict(locations)
        
        # Generate map
        logger.info("🗺️  Generating interactive map...")
        map_obj = geo_processor.create_map_with_clusters(results_df)
        map_path = os.path.join(app.config['OUTPUT_FOLDER'], 'map_with_clustering.html')
        map_obj.save(map_path)
        
        # Save results
        results_df.to_csv(os.path.join(app.config['OUTPUT_FOLDER'], 'results.csv'), index=False)
        
        logger.info("✅ Processing complete!")
        
        return jsonify({
            'success': True,
            'total_images': len(results_df),
            'clusters': len(results_df['cluster'].unique()),
            'map_path': 'map_with_clustering.html',
            'summary': {
                'images_processed': len(results_df),
                'clusters_found': int(results_df['cluster'].nunique()),
                'images_with_gps': len(results_df)
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/map_with_clustering.html')
def show_map():
    """Serve the map file"""
    map_path = os.path.join(app.config['OUTPUT_FOLDER'], 'map_with_clustering.html')
    if os.path.exists(map_path):
        return send_file(map_path)
    return "Map not found", 404

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get stats"""
    upload_dir = app.config['UPLOAD_FOLDER']
    files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
    
    return jsonify({
        'total_images': len(files),
        'max_allowed': MAX_FILES
    }), 200

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    logger.info("🚀 Starting Geospatial Image Analysis Server...")
    app.run(debug=True, host='0.0.0.0', port=5000)