"""
F1 + F2 : Acquisition et prétraitement des images Sentinel-2.

Ce module gère :
- L'authentification avec Copernicus Data Space
- La recherche et le téléchargement d'images Sentinel-2 L2A
- Le prétraitement : extraction des bandes, masquage nuages, découpage en patches
"""
import os
import json
import numpy as np
import requests
from datetime import datetime
from typing import Optional, Tuple, List, Dict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    COPERNICUS_API_URL, COPERNICUS_TOKEN_URL,
    SATELLITE_DIR, PROCESSED_DIR,
    CLOUD_COVER_THRESHOLD, PATCH_SIZE, PATCH_OVERLAP,
    SENTINEL_BANDS, DEFAULT_BBOX
)


class SentinelDownloader:
    """
    Téléchargeur d'images Sentinel-2 L2A depuis Copernicus Data Space.
    
    Utilise l'API OData de Copernicus pour :
    1. Authentifier l'utilisateur (OIDC)
    2. Chercher des produits par zone, date et couverture nuageuse
    3. Télécharger les fichiers .jp2
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Args:
            username: Identifiant Copernicus Data Space (optionnel, utilise env var sinon)
            password: Mot de passe Copernicus (optionnel, utilise env var sinon)
        """
        self.username = username or os.environ.get("COPERNICUS_USER", "")
        self.password = password or os.environ.get("COPERNICUS_PASS", "")
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self) -> bool:
        """
        Obtenir un token d'accès via OIDC.
        
        Returns:
            True si l'authentification réussit
        """
        if not self.username or not self.password:
            print("⚠️  Identifiants Copernicus non configurés. Mode démo recommandé.")
            return False
        
        try:
            response = self.session.post(
                COPERNICUS_TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                    "client_id": "cdse-public",
                },
                timeout=30,
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Authentification Copernicus réussie.")
            return True
        except Exception as e:
            print(f"❌ Erreur d'authentification: {e}")
            return False
    
    def search_products(
        self,
        bbox: Optional[Dict] = None,
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
        max_cloud_cover: int = CLOUD_COVER_THRESHOLD,
        max_results: int = 10,
    ) -> List[Dict]:
        """
        Chercher des produits Sentinel-2 L2A.
        
        Args:
            bbox: Bounding box {"west", "south", "east", "north"}
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            max_cloud_cover: Couverture nuageuse max en %
            max_results: Nombre max de résultats
            
        Returns:
            Liste de produits trouvés
        """
        if bbox is None:
            bbox = DEFAULT_BBOX
        
        # Construire le filtre OData
        footprint = (
            f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(("
            f"{bbox['west']} {bbox['south']},"
            f"{bbox['east']} {bbox['south']},"
            f"{bbox['east']} {bbox['north']},"
            f"{bbox['west']} {bbox['north']},"
            f"{bbox['west']} {bbox['south']}))')"
        )
        
        filter_query = (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and "
            f"ContentDate/Start gt {start_date}T00:00:00.000Z and "
            f"ContentDate/Start lt {end_date}T23:59:59.999Z and "
            f"{footprint} and "
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud_cover})"
        )
        
        try:
            response = self.session.get(
                f"{COPERNICUS_API_URL}/Products",
                params={
                    "$filter": filter_query,
                    "$top": max_results,
                    "$orderby": "ContentDate/Start desc",
                },
                timeout=60,
            )
            response.raise_for_status()
            results = response.json().get("value", [])
            print(f"📡 {len(results)} produits Sentinel-2 trouvés.")
            return results
        except Exception as e:
            print(f"❌ Erreur de recherche: {e}")
            return []
    
    def download_product(self, product_id: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Télécharger un produit Sentinel-2 par son ID.
        
        Args:
            product_id: ID du produit Copernicus
            output_dir: Répertoire de sortie
            
        Returns:
            Chemin du fichier téléchargé ou None
        """
        if output_dir is None:
            output_dir = SATELLITE_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{product_id}.zip")
        
        if os.path.exists(output_path):
            print(f"📁 Produit déjà en cache: {output_path}")
            return output_path
        
        try:
            url = f"{COPERNICUS_API_URL}/Products({product_id})/$value"
            response = self.session.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total = int(response.headers.get("content-length", 0))
            with open(output_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = (downloaded / total) * 100
                        print(f"\r⬇️  Téléchargement: {pct:.1f}%", end="", flush=True)
            
            print(f"\n✅ Téléchargé: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Erreur de téléchargement: {e}")
            return None


class SatellitePreprocessor:
    """
    Prétraitement des images Sentinel-2.
    
    - Lecture des bandes spectrales
    - Masquage des nuages (SCL)
    - Calcul NDVI / NDMI
    - Découpage en patches 256×256
    - Normalisation
    """
    
    def __init__(self, patch_size: int = PATCH_SIZE, overlap: int = PATCH_OVERLAP):
        self.patch_size = patch_size
        self.overlap = overlap
    
    def read_band(self, filepath: str) -> np.ndarray:
        """
        Lire une bande spectrale depuis un fichier .jp2 ou .tif.
        
        Args:
            filepath: Chemin vers le fichier de la bande
            
        Returns:
            Array 2D de la bande
        """
        try:
            import rasterio
            with rasterio.open(filepath) as src:
                band = src.read(1).astype(np.float32)
                # Normaliser les valeurs de réflectance [0, 10000] → [0, 1]
                band = band / 10000.0
                band = np.clip(band, 0, 1)
                return band
        except ImportError:
            print("⚠️  rasterio non installé. Utilisation de données synthétiques.")
            return np.random.rand(1024, 1024).astype(np.float32) * 0.8
    
    def apply_cloud_mask(self, data: np.ndarray, scl: np.ndarray) -> np.ndarray:
        """
        Appliquer le masque de nuages SCL (Scene Classification Layer).
        
        Valeurs SCL à masquer :
        - 3: Cloud shadow
        - 8: Cloud medium probability
        - 9: Cloud high probability
        - 10: Thin cirrus
        
        Args:
            data: Données de la bande
            scl: Couche SCL
            
        Returns:
            Données masquées (NaN pour les pixels nuageux)
        """
        cloud_mask = np.isin(scl, [3, 8, 9, 10])
        masked = data.copy()
        masked[cloud_mask] = np.nan
        return masked
    
    def compute_ndvi(self, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Calculer le NDVI (Normalized Difference Vegetation Index).
        NDVI = (NIR - Red) / (NIR + Red)
        """
        denominator = nir + red
        ndvi = np.where(
            denominator > 0,
            (nir - red) / denominator,
            0.0
        )
        return np.clip(ndvi, -1, 1).astype(np.float32)
    
    def compute_ndmi(self, nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
        """
        Calculer le NDMI (Normalized Difference Moisture Index).
        NDMI = (NIR - SWIR) / (NIR + SWIR)
        """
        denominator = nir + swir
        ndmi = np.where(
            denominator > 0,
            (nir - swir) / denominator,
            0.0
        )
        return np.clip(ndmi, -1, 1).astype(np.float32)
    
    def extract_patches(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Découper une image en patches de taille fixe avec chevauchement.
        
        Args:
            image: Image 2D ou 3D (C, H, W)
            
        Returns:
            Liste de patches numpy
        """
        if image.ndim == 2:
            image = image[np.newaxis, :, :]  # Ajouter dimension canal
        
        _, h, w = image.shape
        step = self.patch_size - self.overlap
        patches = []
        
        for y in range(0, h - self.patch_size + 1, step):
            for x in range(0, w - self.patch_size + 1, step):
                patch = image[:, y:y + self.patch_size, x:x + self.patch_size]
                # Ignorer les patches avec trop de NaN
                if np.isnan(patch).mean() < 0.3:
                    # Remplacer NaN par 0
                    patch = np.nan_to_num(patch, nan=0.0)
                    patches.append(patch)
        
        return patches
    
    def process_scene(
        self,
        red: np.ndarray,
        nir: np.ndarray,
        swir: np.ndarray,
        scl: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray]]:
        """
        Pipeline complet de traitement d'une scène.
        
        Args:
            red: Bande B04 (Red)
            nir: Bande B08 (NIR)
            swir: Bande B11 (SWIR)
            scl: Scene Classification Layer (optionnel)
            
        Returns:
            (ndvi, ndmi, patches) - Indices + patches prêts pour le modèle
        """
        # Masquer les nuages si SCL disponible
        if scl is not None:
            red = self.apply_cloud_mask(red, scl)
            nir = self.apply_cloud_mask(nir, scl)
            swir = self.apply_cloud_mask(swir, scl)
        
        # Calculer les indices
        ndvi = self.compute_ndvi(red, nir)
        ndmi = self.compute_ndmi(nir, swir)
        
        # Empiler les canaux : [NDVI, NDMI, Red]
        stacked = np.stack([ndvi, ndmi, red], axis=0)
        
        # Découper en patches
        patches = self.extract_patches(stacked)
        
        print(f"📊 NDVI range: [{np.nanmin(ndvi):.3f}, {np.nanmax(ndvi):.3f}]")
        print(f"📊 NDMI range: [{np.nanmin(ndmi):.3f}, {np.nanmax(ndmi):.3f}]")
        print(f"🧩 {len(patches)} patches extraits ({self.patch_size}×{self.patch_size})")
        
        return ndvi, ndmi, patches
    
    def save_patches(self, patches: List[np.ndarray], output_dir: Optional[str] = None, prefix: str = "patch"):
        """
        Sauvegarder les patches en format .npy.
        """
        if output_dir is None:
            output_dir = PROCESSED_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i, patch in enumerate(patches):
            filepath = os.path.join(output_dir, f"{prefix}_{i:04d}.npy")
            np.save(filepath, patch)
        
        print(f"💾 {len(patches)} patches sauvegardés dans {output_dir}")


if __name__ == "__main__":
    # Test rapide
    print("=== Test SatellitePreprocessor ===")
    preprocessor = SatellitePreprocessor()
    
    # Simuler des bandes
    h, w = 512, 512
    red = np.random.rand(h, w).astype(np.float32) * 0.3
    nir = np.random.rand(h, w).astype(np.float32) * 0.7 + 0.2
    swir = np.random.rand(h, w).astype(np.float32) * 0.4
    
    ndvi, ndmi, patches = preprocessor.process_scene(red, nir, swir)
    print(f"✅ Test réussi : {len(patches)} patches générés")
