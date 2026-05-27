"""
Configuration for Flask API
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'
CHROMA_DIR = BASE_DIR / 'chroma_db'

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# Flask config
class Config:
    # Basic
    DEBUG = False
    TESTING = False
    
    # Upload
    UPLOAD_FOLDER = str(UPLOAD_DIR)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'tiff', 'heic', 'gif', 'bmp'}
    
    # CORS
    CORS_ORIGINS = ["http://localhost:5000", "http://localhost:3000", "*"]
    
    # Limits
    MAX_IMAGES_PER_UPLOAD = 20
    MAX_PROCESSING_TIME = 600  # 10 minutes
    
    # Paths
    CHROMADB_PATH = str(CHROMA_DIR)
    OUTPUT_PATH = str(OUTPUT_DIR)

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    CORS_ORIGINS = [
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ]

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    UPLOAD_FOLDER = str(UPLOAD_DIR / 'test')

# Select config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
