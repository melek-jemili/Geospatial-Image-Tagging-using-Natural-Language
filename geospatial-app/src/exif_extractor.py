# src/exif_extractor.py
from PIL import Image
import exifread  # Alternative: pip install exifread

def get_gps_from_exif(image_path):
    """
    Extract GPS coordinates (latitude, longitude) from image EXIF data.
    Returns (lat, lon) as floats, or (None, None) if not available.
    """
    try:
        # Open image and read EXIF
        img = Image.open(image_path)
        exif_data = img._getexif()
        
        if not exif_data:
            return None, None
        
        # GPS tags (standard EXIF GPS keys)
        gps_tags = {
            'GPSLatitude': None,
            'GPSLatitudeRef': None,
            'GPSLongitude': None,
            'GPSLongitudeRef': None
        }
        
        for tag, value in exif_data.items():
            tag_name = Image.ExifTags.TAGS.get(tag, tag)
            if tag_name in gps_tags:
                gps_tags[tag_name] = value
        
        if not all(gps_tags.values()):
            return None, None
        
        # Convert DMS to decimal degrees
        def dms_to_decimal(dms, ref):
            degrees, minutes, seconds = dms
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal
        
        lat = dms_to_decimal(gps_tags['GPSLatitude'], gps_tags['GPSLatitudeRef'])
        lon = dms_to_decimal(gps_tags['GPSLongitude'], gps_tags['GPSLongitudeRef'])
        
        return lat, lon
    
    except Exception as e:
        print(f"Error reading EXIF from {image_path}: {e}")
        return None, None

# Alternative using exifread (more robust for GPS)
def get_gps_exifread(image_path):
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)
    
    if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
        lat_dms = tags['GPS GPSLatitude'].values
        lon_dms = tags['GPS GPSLongitude'].values
        lat_ref = str(tags.get('GPS GPSLatitudeRef', 'N'))
        lon_ref = str(tags.get('GPS GPSLongitudeRef', 'E'))
        
        lat = dms_to_decimal(lat_dms, lat_ref)
        lon = dms_to_decimal(lon_dms, lon_ref)
        return lat, lon
    return None, None

def dms_to_decimal(dms, ref):
    # Same as above
    pass