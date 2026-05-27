# src/exif_extractor.py
"""
Advanced GPS metadata extractor for georeferenced images.
Supports JPEG, JPEG2000, PNG, TIFF, HEIC, WebP, and most camera formats.
Falls back gracefully across multiple extraction strategies with robust error handling.
"""

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
import re

logger = logging.getLogger(__name__)

# Suppress PIL warnings about unknown EXIF tags
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GPSData:
    """All GPS-related metadata extracted from an image."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None          # metres above/below sea level
    altitude_ref: int = 0                      # 0 = above, 1 = below
    speed: Optional[float] = None             # km/h
    bearing: Optional[float] = None           # degrees true north
    timestamp: Optional[str] = None           # "HH:MM:SS UTC"
    datestamp: Optional[str] = None           # "YYYY:MM:DD"
    dop: Optional[float] = None               # dilution of precision
    fix_type: Optional[str] = None            # "2D" / "3D"
    source: str = "unknown"                   # which library extracted it

    @property
    def coords(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)

    def __str__(self) -> str:
        parts = [f"lat={self.latitude:.6f}, lon={self.longitude:.6f}"]
        if self.altitude is not None:
            sign = "-" if self.altitude_ref else "+"
            parts.append(f"alt={sign}{self.altitude:.1f}m")
        if self.timestamp:
            parts.append(self.timestamp)
        return f"GPSData({', '.join(parts)}, via={self.source})"


@dataclass
class ImageMetadata:
    """Full metadata bundle returned to the caller."""
    path: str
    gps: Optional[GPSData] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    datetime_original: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    errors: list[str] = field(default_factory=list)

    @property
    def has_gps(self) -> bool:
        return self.gps is not None


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _to_float(value) -> float:
    """
    Safely convert an EXIF rational/tuple/IFDRational to a Python float.
    Handles: int, float, tuple (num, den), exifread IfdTag values,
    Pillow IFDRational objects, and fractions.Fraction.
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Pillow IFDRational or fractions.Fraction
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        try:
            return value.numerator / value.denominator if value.denominator else 0.0
        except Exception as e:
            logger.debug("Error converting IFDRational: %s", e)
            return 0.0
    
    # Plain tuple (numerator, denominator)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        try:
            return value[0] / value[1] if value[1] else 0.0
        except Exception as e:
            logger.debug("Error converting tuple: %s", e)
            return 0.0
    
    # exifread Ratio object
    if hasattr(value, "num") and hasattr(value, "den"):
        try:
            return value.num / value.den if value.den else 0.0
        except Exception as e:
            logger.debug("Error converting Ratio: %s", e)
            return 0.0
    
    # String representation
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            logger.debug("Cannot convert string to float: %s", value)
            return 0.0
    
    try:
        return float(value)
    except Exception as e:
        logger.debug("Cannot convert value to float: %s, Error: %s", value, e)
        return 0.0


def _validate_coordinates(lat: float, lon: float) -> bool:
    """Validate that coordinates are within valid ranges."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def _dms_to_decimal(dms_values, ref: str) -> Optional[float]:
    """
    Convert a DMS (degrees/minutes/seconds) sequence + hemisphere reference
    to signed decimal degrees with validation.

    `dms_values` may be a list/tuple of three rationals or a flat sequence.
    Returns None if conversion fails, otherwise the decimal coordinate.
    """
    try:
        if not dms_values or len(dms_values) < 3:
            logger.debug("Invalid DMS values: %s", dms_values)
            return None
        
        d, m, s = [_to_float(v) for v in dms_values[:3]]
        
        # Validate individual components
        if d < 0 or m < 0 or s < 0:
            logger.debug("Negative DMS values: d=%f, m=%f, s=%f", d, m, s)
            return None
        
        decimal = d + m / 60.0 + s / 3600.0
        
        if ref.upper() in ("S", "W"):
            decimal = -decimal
        
        # Validate final result
        if ref.upper() in ("N", "S") and not (-90 <= decimal <= 90):
            logger.debug("Invalid latitude: %f (ref=%s)", decimal, ref)
            return None
        
        if ref.upper() in ("E", "W") and not (-180 <= decimal <= 180):
            logger.debug("Invalid longitude: %f (ref=%s)", decimal, ref)
            return None
        
        return round(decimal, 8)
    
    except Exception as e:
        logger.debug("DMS conversion error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Strategy 1: Pillow (_getexif)
# ---------------------------------------------------------------------------

def _extract_pillow(image_path: str) -> Optional[GPSData]:
    """Extract GPS data using Pillow's EXIF interface."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        img = Image.open(image_path)
        raw_exif = img._getexif()
        if not raw_exif:
            logger.debug("No EXIF data found in Pillow for: %s", image_path)
            return None

        # Decode all EXIF tags
        exif = {TAGS.get(k, k): v for k, v in raw_exif.items()}

        gps_raw = exif.get("GPSInfo")
        if not gps_raw:
            logger.debug("No GPSInfo tag in EXIF")
            return None

        # Decode GPS sub-IFD
        gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

        lat_dms  = gps.get("GPSLatitude")
        lat_ref  = str(gps.get("GPSLatitudeRef", "N")).strip()
        lon_dms  = gps.get("GPSLongitude")
        lon_ref  = str(gps.get("GPSLongitudeRef", "E")).strip()

        if not (lat_dms and lon_dms):
            logger.debug("Missing latitude or longitude in GPS data")
            return None

        # Clean up references - ensure they're single characters
        lat_ref = lat_ref[0].upper() if lat_ref else "N"
        lon_ref = lon_ref[0].upper() if lon_ref else "E"
        
        if lat_ref not in ("N", "S"):
            lat_ref = "N"
        if lon_ref not in ("E", "W"):
            lon_ref = "E"

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)
        
        if lat is None or lon is None:
            logger.debug("Failed to convert DMS to decimal")
            return None

        # Optional extras
        alt, alt_ref, speed, bearing, dop, fix_type = None, 0, None, None, None, None

        if "GPSAltitude" in gps:
            try:
                alt = _to_float(gps["GPSAltitude"])
                alt_ref = int(_to_float(gps.get("GPSAltitudeRef", 0)))
            except Exception as e:
                logger.debug("Error reading altitude: %s", e)

        if "GPSSpeed" in gps:
            try:
                speed_raw = _to_float(gps["GPSSpeed"])
                speed_unit = str(gps.get("GPSSpeedRef", "K")).upper().strip()
                if speed_unit in ("M", "K", "N"):
                    speed = speed_raw * (1.60934 if speed_unit == "M" else
                                          1.85200 if speed_unit == "N" else 1.0)
            except Exception as e:
                logger.debug("Error reading speed: %s", e)

        if "GPSTrack" in gps:
            try:
                bearing = _to_float(gps["GPSTrack"])
            except Exception as e:
                logger.debug("Error reading bearing: %s", e)

        if "GPSDOP" in gps:
            try:
                dop = _to_float(gps["GPSDOP"])
            except Exception as e:
                logger.debug("Error reading DOP: %s", e)

        if "GPSMeasureMode" in gps:
            try:
                mode = str(gps["GPSMeasureMode"]).strip()
                fix_type = "3D" if mode == "3" else "2D"
            except Exception as e:
                logger.debug("Error reading measure mode: %s", e)

        # GPS timestamp
        ts, ds = None, None
        if "GPSTimeStamp" in gps:
            try:
                h, m, s = [_to_float(x) for x in gps["GPSTimeStamp"]]
                ts = f"{int(h):02d}:{int(m):02d}:{s:05.2f} UTC"
            except Exception as e:
                logger.debug("Error reading timestamp: %s", e)
        
        if "GPSDateStamp" in gps:
            try:
                ds = str(gps["GPSDateStamp"])
            except Exception as e:
                logger.debug("Error reading datestamp: %s", e)

        logger.info("Successfully extracted GPS from Pillow: lat=%f, lon=%f", lat, lon)
        return GPSData(
            latitude=lat, longitude=lon,
            altitude=alt, altitude_ref=alt_ref,
            speed=speed, bearing=bearing,
            timestamp=ts, datestamp=ds,
            dop=dop, fix_type=fix_type,
            source="pillow",
        )

    except Exception as e:
        logger.debug("Pillow extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Strategy 2: exifread (more robust for RAW / unusual JPEG)
# ---------------------------------------------------------------------------

def _extract_exifread(image_path: str) -> Optional[GPSData]:
    """Extract GPS data using the exifread library."""
    try:
        import exifread

        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)

        def tag(name):
            t = tags.get(name)
            return t.values if t else None

        lat_vals = tag("GPS GPSLatitude")
        lon_vals = tag("GPS GPSLongitude")
        if not (lat_vals and lon_vals):
            logger.debug("No GPS latitude or longitude in exifread")
            return None

        lat_ref = str(tag("GPS GPSLatitudeRef")  or ["N"])[0]
        lon_ref = str(tag("GPS GPSLongitudeRef") or ["E"])[0]

        # Ensure valid references
        lat_ref = lat_ref[0].upper() if lat_ref else "N"
        lon_ref = lon_ref[0].upper() if lon_ref else "E"
        
        if lat_ref not in ("N", "S"):
            lat_ref = "N"
        if lon_ref not in ("E", "W"):
            lon_ref = "E"

        lat = _dms_to_decimal(lat_vals, lat_ref)
        lon = _dms_to_decimal(lon_vals, lon_ref)
        
        if lat is None or lon is None:
            logger.debug("Failed to convert DMS to decimal in exifread")
            return None

        alt, alt_ref, speed, bearing, dop, fix_type = None, 0, None, None, None, None

        if tag("GPS GPSAltitude"):
            try:
                alt = _to_float(tag("GPS GPSAltitude")[0])
                ar  = tag("GPS GPSAltitudeRef")
                alt_ref = int(_to_float(ar[0])) if ar else 0
            except Exception as e:
                logger.debug("Error reading altitude in exifread: %s", e)

        if tag("GPS GPSSpeed"):
            try:
                speed = _to_float(tag("GPS GPSSpeed")[0])
            except Exception as e:
                logger.debug("Error reading speed in exifread: %s", e)

        if tag("GPS GPSTrack"):
            try:
                bearing = _to_float(tag("GPS GPSTrack")[0])
            except Exception as e:
                logger.debug("Error reading bearing in exifread: %s", e)

        if tag("GPS GPSDOP"):
            try:
                dop = _to_float(tag("GPS GPSDOP")[0])
            except Exception as e:
                logger.debug("Error reading DOP in exifread: %s", e)

        ts_vals = tag("GPS GPSTimeStamp")
        ts = None
        if ts_vals:
            try:
                h, m, s = [_to_float(x) for x in ts_vals]
                ts = f"{int(h):02d}:{int(m):02d}:{s:05.2f} UTC"
            except Exception as e:
                logger.debug("Error reading timestamp in exifread: %s", e)

        ds_vals = tag("GPS GPSDate")
        ds = str(ds_vals[0]) if ds_vals else None

        logger.info("Successfully extracted GPS from exifread: lat=%f, lon=%f", lat, lon)
        return GPSData(
            latitude=lat, longitude=lon,
            altitude=alt, altitude_ref=alt_ref,
            speed=speed, bearing=bearing,
            timestamp=ts, datestamp=ds,
            dop=dop, fix_type=fix_type,
            source="exifread",
        )

    except Exception as e:
        logger.debug("exifread extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Strategy 3: piexif (write-capable, good fallback)
# ---------------------------------------------------------------------------

def _extract_piexif(image_path: str) -> Optional[GPSData]:
    """Extract GPS data using piexif."""
    try:
        import piexif

        exif = piexif.load(image_path)
        gps = exif.get("GPS", {})

        lat_dms = gps.get(piexif.GPSIFD.GPSLatitude)
        lon_dms = gps.get(piexif.GPSIFD.GPSLongitude)
        if not (lat_dms and lon_dms):
            logger.debug("No GPS latitude or longitude in piexif")
            return None

        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef,  b"N").decode()
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode()

        # Ensure valid references
        lat_ref = lat_ref[0].upper() if lat_ref else "N"
        lon_ref = lon_ref[0].upper() if lon_ref else "E"
        
        if lat_ref not in ("N", "S"):
            lat_ref = "N"
        if lon_ref not in ("E", "W"):
            lon_ref = "E"

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)

        if lat is None or lon is None:
            logger.debug("Failed to convert DMS to decimal in piexif")
            return None

        alt, alt_ref = None, 0
        if piexif.GPSIFD.GPSAltitude in gps:
            try:
                alt = _to_float(gps[piexif.GPSIFD.GPSAltitude])
                alt_ref = gps.get(piexif.GPSIFD.GPSAltitudeRef, 0)
            except Exception as e:
                logger.debug("Error reading altitude in piexif: %s", e)

        logger.info("Successfully extracted GPS from piexif: lat=%f, lon=%f", lat, lon)
        return GPSData(
            latitude=lat, longitude=lon,
            altitude=alt, altitude_ref=alt_ref,
            source="piexif",
        )

    except Exception as e:
        logger.debug("piexif extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Strategy 4: rawpy (for RAW files)
# ---------------------------------------------------------------------------

def _extract_rawpy(image_path: str) -> Optional[GPSData]:
    """Extract GPS data using rawpy library for RAW formats."""
    try:
        import rawpy
        import numpy as np

        with rawpy.imread(image_path) as raw:
            # Try to get EXIF data from raw image
            if hasattr(raw, 'exif'):
                exif_dict = raw.exif
                if exif_dict:
                    # Attempt to parse GPS from raw EXIF
                    logger.debug("Extracted EXIF from RAW file")
                    # Note: rawpy doesn't easily expose GPS, fallback to piexif
                    return None
        return None
    except Exception as e:
        logger.debug("rawpy extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_STRATEGIES = [_extract_pillow, _extract_exifread, _extract_piexif]


def extract_metadata(image_path: str) -> ImageMetadata:
    """
    Extract full metadata (GPS + camera info) from an image file.

    Tries multiple libraries in order of preference and returns the first
    successful GPS result.  Camera/capture metadata is always extracted
    via Pillow when available.

    Parameters
    ----------
    image_path : str | Path
        Absolute or relative path to the image file.

    Returns
    -------
    ImageMetadata
        Always returns an object; check `.has_gps` before using `.gps`.
    """
    path = str(image_path)
    meta = ImageMetadata(path=path)

    if not Path(path).exists():
        meta.errors.append(f"File not found: {path}")
        return meta

    # --- Camera info via Pillow (doesn't need GPS) ---
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(path)
        meta.width, meta.height = img.size

        raw = img._getexif() or {}
        exif = {TAGS.get(k, k): v for k, v in raw.items()}
        meta.camera_make  = exif.get("Make")
        meta.camera_model = exif.get("Model")
        meta.datetime_original = (
            exif.get("DateTimeOriginal") or exif.get("DateTime")
        )
    except Exception as e:
        meta.errors.append(f"Camera info unavailable: {e}")

    # --- GPS via fallback chain ---
    for strategy in _STRATEGIES:
        gps = strategy(path)
        if gps is not None:
            meta.gps = gps
            logger.info("GPS extracted via %s from %s", gps.source, path)
            break
    else:
        meta.errors.append("No GPS data found in EXIF (tried all strategies).")

    return meta


# Convenience shorthand kept for backward compatibility
def get_gps(image_path: str) -> tuple[Optional[float], Optional[float]]:
    """Return (latitude, longitude) or (None, None) — quick one-liner."""
    meta = extract_metadata(image_path)
    if meta.has_gps:
        return meta.gps.coords
    return None, None


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python exif_extractor.py <image_path> [image_path ...]")
        sys.exit(1)

    results = []
    for img_path in sys.argv[1:]:
        m = extract_metadata(img_path)
        entry = {
            "file":     m.path,
            "camera":   f"{m.camera_make or ''} {m.camera_model or ''}".strip() or None,
            "datetime": m.datetime_original,
            "size":     f"{m.width}x{m.height}" if m.width else None,
            "gps":      None,
            "errors":   m.errors,
        }
        if m.has_gps:
            g = m.gps
            entry["gps"] = {
                "latitude":   g.latitude,
                "longitude":  g.longitude,
                "altitude_m": g.altitude,
                "speed_kmh":  g.speed,
                "bearing":    g.bearing,
                "timestamp":  g.timestamp,
                "datestamp":  g.datestamp,
                "dop":        g.dop,
                "fix_type":   g.fix_type,
                "source":     g.source,
            }
        results.append(entry)

    print(json.dumps(results, indent=2, ensure_ascii=False))