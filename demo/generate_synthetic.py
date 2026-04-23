"""
Générateur de données synthétiques pour le mode démo.

Génère des données réalistes pour tester l'ensemble du pipeline
sans accès aux API externes :
- Patches satellite avec patterns de stress
- Données météo saisonnières
- Lectures de capteurs IoT
"""
import os
import sys
import numpy as np
import pandas as pd
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SYNTHETIC_DIR, PATCH_SIZE, PROCESSED_DIR


def generate_stress_pattern(size: int = 256, seed: int = None) -> np.ndarray:
    """
    Générer un pattern réaliste de stress hydrique.
    
    Utilise des gaussiennes pour créer des zones de stress
    qui ressemblent à des patterns agricoles réels.
    """
    if seed is not None:
        np.random.seed(seed)
    
    stress = np.zeros((size, size), dtype=np.float32)
    
    # Ajouter 2-5 zones de stress aléatoires (gaussiennes)
    n_zones = np.random.randint(2, 6)
    for _ in range(n_zones):
        cx = np.random.randint(size // 4, 3 * size // 4)
        cy = np.random.randint(size // 4, 3 * size // 4)
        sx = np.random.randint(20, 60)
        sy = np.random.randint(20, 60)
        intensity = np.random.uniform(0.5, 1.0)
        
        y, x = np.ogrid[:size, :size]
        gaussian = np.exp(-((x - cx)**2 / (2*sx**2) + (y - cy)**2 / (2*sy**2)))
        stress += gaussian * intensity
    
    # Ajouter du bruit de grain
    stress += np.random.normal(0, 0.05, (size, size))
    
    # Normaliser [0, 1]
    stress = np.clip(stress, 0, 1)
    
    return stress


def generate_synthetic_patch(size: int = 256, seed: int = None) -> tuple:
    """
    Générer un patch satellite synthétique avec son masque de stress.
    
    Returns:
        (image, mask) où image est (3, H, W) et mask est (H, W) avec classes 0–3
    """
    if seed is not None:
        np.random.seed(seed)
    
    stress_intensity = generate_stress_pattern(size, seed)
    
    # Générer NDVI (corrélé inversement au stress)
    ndvi_base = 0.6 - 0.4 * stress_intensity
    ndvi = ndvi_base + np.random.normal(0, 0.03, (size, size))
    ndvi = np.clip(ndvi, 0, 0.9).astype(np.float32)
    
    # Générer NDMI (corrélé inversement au stress, avec plus de variabilité)
    ndmi_base = 0.3 - 0.4 * stress_intensity
    ndmi = ndmi_base + np.random.normal(0, 0.04, (size, size))
    ndmi = np.clip(ndmi, -0.3, 0.5).astype(np.float32)
    
    # Bande Red (corrélé au stress : plus de rouge = moins de végétation)
    red = 0.15 + 0.25 * stress_intensity + np.random.normal(0, 0.02, (size, size))
    red = np.clip(red, 0, 0.5).astype(np.float32)
    
    # Empiler : [NDVI, NDMI, Red]
    image = np.stack([ndvi, ndmi, red], axis=0)
    
    # Générer le masque de stress (4 classes)
    mask = np.zeros((size, size), dtype=np.int64)
    mask[stress_intensity < 0.2] = 0   # Normal
    mask[(stress_intensity >= 0.2) & (stress_intensity < 0.4)] = 1  # Léger
    mask[(stress_intensity >= 0.4) & (stress_intensity < 0.7)] = 2  # Modéré
    mask[stress_intensity >= 0.7] = 3  # Sévère
    
    return image, mask


def generate_synthetic_dataset(
    n_samples: int = 200,
    output_dir: str = None,
    patch_size: int = PATCH_SIZE,
):
    """
    Générer un dataset synthétique complet.
    
    Sauvegarde en format .npz pour un chargement rapide.
    """
    if output_dir is None:
        output_dir = SYNTHETIC_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🎭 Génération de {n_samples} patches synthétiques ({patch_size}×{patch_size})...")
    
    images = np.zeros((n_samples, 3, patch_size, patch_size), dtype=np.float32)
    masks = np.zeros((n_samples, patch_size, patch_size), dtype=np.int64)
    
    for i in range(n_samples):
        image, mask = generate_synthetic_patch(patch_size, seed=i)
        images[i] = image
        masks[i] = mask
    
    # Vérifier la distribution des classes
    unique, counts = np.unique(masks, return_counts=True)
    total = masks.size
    print("  Distribution des classes :")
    class_names = {0: "Normal", 1: "Léger", 2: "Modéré", 3: "Sévère"}
    for u, c in zip(unique, counts):
        print(f"    {class_names.get(u, u)}: {c/total*100:.1f}%")
    
    # Sauvegarder
    output_path = os.path.join(output_dir, "synthetic_dataset.npz")
    np.savez_compressed(output_path, images=images, masks=masks)
    print(f"💾 Dataset sauvegardé: {output_path}")
    
    # Sauvegarder aussi en patches individuels pour compatibilité
    patch_dir = os.path.join(output_dir)
    for i in range(min(n_samples, 50)):  # Max 50 fichiers individuels
        np.save(os.path.join(patch_dir, f"patch_{i:04d}.npy"), images[i])
        np.save(os.path.join(patch_dir, f"mask_{i:04d}.npy"), masks[i])
    
    return images, masks


def generate_demo_weather(n_days: int = 365, save: bool = True) -> pd.DataFrame:
    """Générer un jeu de données météo réaliste pour la démo."""
    from pipeline.weather import generate_synthetic_weather, WeatherFetcher
    
    df = generate_synthetic_weather(n_days)
    fetcher = WeatherFetcher()
    df = fetcher.compute_et0(df)
    
    if save:
        os.makedirs(SYNTHETIC_DIR, exist_ok=True)
        path = os.path.join(SYNTHETIC_DIR, "weather_demo.csv")
        df.to_csv(path, index=False)
        print(f"💾 Données météo sauvegardées: {path}")
    
    return df


def generate_demo_iot(weather_df: pd.DataFrame, n_days: int = 30, save: bool = True) -> pd.DataFrame:
    """Générer des données IoT pour la démo."""
    from pipeline.iot import IoTSimulator
    
    simulator = IoTSimulator(num_sensors=5)
    # Utiliser seulement les derniers n_days jours
    recent_weather = weather_df.tail(n_days).reset_index(drop=True)
    readings = simulator.generate_readings(recent_weather)
    summary = simulator.generate_daily_summary(readings)
    
    if save:
        os.makedirs(SYNTHETIC_DIR, exist_ok=True)
        readings_path = os.path.join(SYNTHETIC_DIR, "iot_readings_demo.csv")
        summary_path = os.path.join(SYNTHETIC_DIR, "iot_summary_demo.csv")
        readings.to_csv(readings_path, index=False)
        summary.to_csv(summary_path, index=False)
        print(f"💾 Données IoT sauvegardées: {readings_path}")
    
    return readings


def generate_all_demo_data():
    """Générer toutes les données démo."""
    print("=" * 60)
    print("  🎭 Génération des données de démonstration")
    print("=" * 60)
    
    # 1. Patches satellite
    print("\n📡 1/3 — Patches satellite synthétiques")
    images, masks = generate_synthetic_dataset(n_samples=200)
    
    # 2. Données météo
    print("\n⛅ 2/3 — Données météorologiques")
    weather_df = generate_demo_weather(365)
    
    # 3. Données IoT
    print("\n📡 3/3 — Données capteurs IoT")
    iot_df = generate_demo_iot(weather_df, n_days=30)
    
    print("\n" + "=" * 60)
    print("  ✅ Toutes les données démo ont été générées!")
    print(f"  📁 Répertoire: {SYNTHETIC_DIR}")
    print("=" * 60)
    
    return images, masks, weather_df, iot_df


if __name__ == "__main__":
    generate_all_demo_data()
