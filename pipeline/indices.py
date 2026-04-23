"""
Calcul des indices de végétation et classification du stress hydrique.

Indices :
- NDVI (Normalized Difference Vegetation Index)
- NDMI (Normalized Difference Moisture Index)
"""

import numpy as np
from typing import Dict, Tuple

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import NDVI_THRESHOLDS, NDMI_THRESHOLDS, STRESS_LABELS, STRESS_COLORS


def compute_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    NDVI = (NIR - Red) / (NIR + Red)
    
    Plage : [-1, 1]
    - Valeurs élevées (>0.5) : végétation dense et saine
    - Valeurs faibles (<0.3) : sol nu ou végétation stressée
    """
    denom = nir + red
    ndvi = np.where(denom > 0, (nir - red) / denom, 0.0)
    return np.clip(ndvi, -1, 1).astype(np.float32)


def compute_ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """
    NDMI = (NIR - SWIR) / (NIR + SWIR)
    
    Plage : [-1, 1]
    - Valeurs positives : contenu en eau normal
    - Valeurs négatives : déficit hydrique
    """
    denom = nir + swir
    ndmi = np.where(denom > 0, (nir - swir) / denom, 0.0)
    return np.clip(ndmi, -1, 1).astype(np.float32)


def classify_stress_ndvi(ndvi: np.ndarray) -> np.ndarray:
    """
    Classifier le stress hydrique à partir du NDVI.
    
    Returns:
        Carte de stress : 0=normal, 1=léger, 2=modéré, 3=sévère
    """
    stress = np.zeros_like(ndvi, dtype=np.int32)
    stress[ndvi < NDVI_THRESHOLDS["severe"]] = 3    # Sévère
    stress[(ndvi >= NDVI_THRESHOLDS["severe"]) & (ndvi < NDVI_THRESHOLDS["moderate"])] = 2  # Modéré
    stress[(ndvi >= NDVI_THRESHOLDS["moderate"]) & (ndvi < NDVI_THRESHOLDS["light"])] = 1   # Léger
    stress[ndvi >= NDVI_THRESHOLDS["light"]] = 0    # Normal
    return stress


def classify_stress_combined(ndvi: np.ndarray, ndmi: np.ndarray) -> np.ndarray:
    """
    Classification combinée NDVI + NDMI pour une meilleure précision.
    
    Le NDMI renforce la détection quand la végétation semble ok (NDVI moyen)
    mais manque d'eau (NDMI faible).
    """
    stress = classify_stress_ndvi(ndvi)
    
    # Renforcer le stress si NDMI indique un déficit hydrique
    moisture_deficit = ndmi < NDMI_THRESHOLDS["stress"]
    # Augmenter le stress d'un niveau si déficit hydrique détecté
    stress[moisture_deficit] = np.minimum(stress[moisture_deficit] + 1, 3)
    
    return stress


def compute_stress_statistics(stress_map: np.ndarray) -> Dict:
    """
    Calculer les statistiques de la carte de stress.
    
    Returns:
        Dictionnaire avec les pourcentages par niveau de stress
    """
    total = stress_map.size
    stats = {}
    
    for level, label in STRESS_LABELS.items():
        count = np.sum(stress_map == level)
        percentage = (count / total) * 100 if total > 0 else 0
        stats[label] = {
            "count": int(count),
            "percentage": round(percentage, 2),
            "color": STRESS_COLORS[level],
        }
    
    # Score global de stress (0–1)
    mean_stress = stress_map.mean() / 3.0
    stats["score_global"] = round(float(mean_stress), 4)
    
    return stats


def stress_to_rgb(stress_map: np.ndarray) -> np.ndarray:
    """
    Convertir la carte de stress en image RGB pour la visualisation.
    
    Returns:
        Image RGB (H, W, 3) avec les couleurs de stress
    """
    h, w = stress_map.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    
    color_map = {
        0: (46, 125, 50),     # Vert
        1: (249, 168, 37),    # Jaune
        2: (239, 108, 0),     # Orange
        3: (198, 40, 40),     # Rouge
    }
    
    for level, color in color_map.items():
        mask = stress_map == level
        rgb[mask] = color
    
    return rgb


def ndvi_to_rgb(ndvi: np.ndarray) -> np.ndarray:
    """
    Convertir NDVI en image RGB avec colormap vert-brun.
    """
    h, w = ndvi.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    
    # Normaliser NDVI de [-1,1] à [0,1]
    norm = (ndvi + 1) / 2.0
    norm = np.clip(norm, 0, 1)
    
    # Rouge → Jaune → Vert
    rgb[:, :, 0] = ((1 - norm) * 200).astype(np.uint8)  # R
    rgb[:, :, 1] = (norm * 200 + 55).astype(np.uint8)    # G
    rgb[:, :, 2] = (30).astype(np.uint8)                  # B
    
    return rgb


if __name__ == "__main__":
    print("=== Test Indices ===")
    
    # Données de test
    red = np.random.rand(256, 256).astype(np.float32) * 0.3
    nir = np.random.rand(256, 256).astype(np.float32) * 0.7 + 0.2
    swir = np.random.rand(256, 256).astype(np.float32) * 0.4
    
    ndvi = compute_ndvi(red, nir)
    ndmi = compute_ndmi(nir, swir)
    stress = classify_stress_combined(ndvi, ndmi)
    stats = compute_stress_statistics(stress)
    
    print(f"NDVI: [{ndvi.min():.3f}, {ndvi.max():.3f}]")
    print(f"NDMI: [{ndmi.min():.3f}, {ndmi.max():.3f}]")
    print(f"Stats: {stats}")
    print("✅ Test indices réussi")
