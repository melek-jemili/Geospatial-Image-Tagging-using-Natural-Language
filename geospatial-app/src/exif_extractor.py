# src/exif_extractor.py
"""
Robust GPS metadata extractor for georeferenced images.
Supports JPEG, TIFF, HEIC, and most camera formats.
Falls back gracefully across multiple extraction strategies.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
    if isinstance(value, (int, float)):
        return float(value)
    # Pillow IFDRational or fractions.Fraction
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return value.numerator / value.denominator if value.denominator else 0.0
    # Plain tuple (numerator, denominator)
    if isinstance(value, tuple) and len(value) == 2:
        return value[0] / value[1] if value[1] else 0.0
    # exifread Ratio object
    if hasattr(value, "num") and hasattr(value, "den"):
        return value.num / value.den if value.den else 0.0
    return float(value)


def _dms_to_decimal(dms_values, ref: str) -> float:
    """
    Convert a DMS (degrees/minutes/seconds) sequence + hemisphere reference
    to signed decimal degrees.

    `dms_values` may be a list/tuple of three rationals or a flat sequence.
    """
    d, m, s = [_to_float(v) for v in dms_values[:3]]
    decimal = d + m / 60.0 + s / 3600.0
    if ref.upper() in ("S", "W"):
        decimal = -decimal
    return round(decimal, 8)


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
            return None

        # Decode all EXIF tags
        exif = {TAGS.get(k, k): v for k, v in raw_exif.items()}

        gps_raw = exif.get("GPSInfo")
        if not gps_raw:
            return None

        # Decode GPS sub-IFD
        gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

        lat_dms  = gps.get("GPSLatitude")
        lat_ref  = str(gps.get("GPSLatitudeRef", "N")).strip()
        lon_dms  = gps.get("GPSLongitude")
        lon_ref  = str(gps.get("GPSLongitudeRef", "E")).strip()

        if not (lat_dms and lon_dms):
            return None

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)

        # Optional extras
        alt, alt_ref, speed, bearing, dop, fix_type = None, 0, None, None, None, None

        if "GPSAltitude" in gps:
            alt = _to_float(gps["GPSAltitude"])
            alt_ref = int(_to_float(gps.get("GPSAltitudeRef", 0)))

        if "GPSSpeed" in gps:
            speed_raw = _to_float(gps["GPSSpeed"])
            speed_unit = str(gps.get("GPSSpeedRef", "K")).upper()
            speed = speed_raw * (1.60934 if speed_unit == "M" else
                                  1.85200 if speed_unit == "N" else 1.0)

        if "GPSTrack" in gps:
            bearing = _to_float(gps["GPSTrack"])

        if "GPSDOP" in gps:
            dop = _to_float(gps["GPSDOP"])

        if "GPSMeasureMode" in gps:
            mode = str(gps["GPSMeasureMode"]).strip()
            fix_type = "3D" if mode == "3" else "2D"

        # GPS timestamp
        ts, ds = None, None
        if "GPSTimeStamp" in gps:
            h, m, s = [_to_float(x) for x in gps["GPSTimeStamp"]]
            ts = f"{int(h):02d}:{int(m):02d}:{s:05.2f} UTC"
        if "GPSDateStamp" in gps:
            ds = str(gps["GPSDateStamp"])

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
            return None

        lat_ref = str(tag("GPS GPSLatitudeRef")  or ["N"])[0]
        lon_ref = str(tag("GPS GPSLongitudeRef") or ["E"])[0]

        lat = _dms_to_decimal(lat_vals, lat_ref)
        lon = _dms_to_decimal(lon_vals, lon_ref)

        alt, alt_ref, speed, bearing, dop, fix_type = None, 0, None, None, None, None

        if tag("GPS GPSAltitude"):
            alt = _to_float(tag("GPS GPSAltitude")[0])
            ar  = tag("GPS GPSAltitudeRef")
            alt_ref = int(_to_float(ar[0])) if ar else 0

        if tag("GPS GPSSpeed"):
            speed = _to_float(tag("GPS GPSSpeed")[0])

        if tag("GPS GPSTrack"):
            bearing = _to_float(tag("GPS GPSTrack")[0])

        if tag("GPS GPSDOP"):
            dop = _to_float(tag("GPS GPSDOP")[0])

        ts_vals = tag("GPS GPSTimeStamp")
        ts = None
        if ts_vals:
            h, m, s = [_to_float(x) for x in ts_vals]
            ts = f"{int(h):02d}:{int(m):02d}:{s:05.2f} UTC"

        ds_vals = tag("GPS GPSDate")
        ds = str(ds_vals[0]) if ds_vals else None

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
            return None

        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef,  b"N").decode()
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode()

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)

        alt, alt_ref = None, 0
        if piexif.GPSIFD.GPSAltitude in gps:
            alt = _to_float(gps[piexif.GPSIFD.GPSAltitude])
            alt_ref = gps.get(piexif.GPSIFD.GPSAltitudeRef, 0)

        return GPSData(
            latitude=lat, longitude=lon,
            altitude=alt, altitude_ref=alt_ref,
            source="piexif",
        )

    except Exception as e:
        logger.debug("piexif extraction failed: %s", e)
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