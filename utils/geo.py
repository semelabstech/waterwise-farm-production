"""
Utilitaires géospatiaux.
"""
import numpy as np
from typing import Dict, Tuple


def bbox_to_polygon(bbox: Dict) -> list:
    """Convertir un bounding box en polygone GeoJSON."""
    return [
        [bbox["west"], bbox["south"]],
        [bbox["east"], bbox["south"]],
        [bbox["east"], bbox["north"]],
        [bbox["west"], bbox["north"]],
        [bbox["west"], bbox["south"]],
    ]


def polygon_area_km2(bbox: Dict) -> float:
    """Calculer l'aire approximative d'un bbox en km²."""
    lat_mid = (bbox["south"] + bbox["north"]) / 2
    lat_dist = abs(bbox["north"] - bbox["south"]) * 111.0
    lon_dist = abs(bbox["east"] - bbox["west"]) * 111.0 * np.cos(np.radians(lat_mid))
    return round(lat_dist * lon_dist, 2)


def pixel_to_geo(
    pixel_x: int, pixel_y: int,
    bbox: Dict, img_width: int, img_height: int
) -> Tuple[float, float]:
    """Convertir des coordonnées pixel en coordonnées géographiques."""
    lon = bbox["west"] + (pixel_x / img_width) * (bbox["east"] - bbox["west"])
    lat = bbox["north"] - (pixel_y / img_height) * (bbox["north"] - bbox["south"])
    return round(lat, 6), round(lon, 6)


def geo_to_pixel(
    lat: float, lon: float,
    bbox: Dict, img_width: int, img_height: int
) -> Tuple[int, int]:
    """Convertir des coordonnées géographiques en coordonnées pixel."""
    x = int((lon - bbox["west"]) / (bbox["east"] - bbox["west"]) * img_width)
    y = int((bbox["north"] - lat) / (bbox["north"] - bbox["south"]) * img_height)
    return x, y


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km entre deux points GPS (formule de Haversine)."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return round(R * c, 3)


def generate_grid_points(bbox: Dict, n_rows: int = 5, n_cols: int = 5) -> list:
    """Générer une grille de points dans un bbox."""
    lats = np.linspace(bbox["south"], bbox["north"], n_rows)
    lons = np.linspace(bbox["west"], bbox["east"], n_cols)
    points = []
    for lat in lats:
        for lon in lons:
            points.append({"lat": round(lat, 6), "lon": round(lon, 6)})
    return points
