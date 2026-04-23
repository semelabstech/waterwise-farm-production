"""
Dataset PyTorch pour les patches satellite.

Gère le chargement des patches pré-traités et les augmentations de données.
"""
import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from typing import Optional, Tuple, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import PROCESSED_DIR, SYNTHETIC_DIR, PATCH_SIZE, UNET_CONFIG


class SatelliteDataset(Dataset):
    """
    Dataset de patches satellite pour l'entraînement U-Net.
    
    Chaque échantillon contient :
    - image: Tensor (3, H, W) — [NDVI, NDMI, Red]
    - mask: Tensor (H, W) — carte de stress [0, 1, 2, 3]
    """
    
    def __init__(
        self,
        data_dir: str = PROCESSED_DIR,
        augment: bool = False,
        patch_size: int = PATCH_SIZE,
    ):
        self.data_dir = data_dir
        self.augment = augment
        self.patch_size = patch_size
        
        # Charger les fichiers
        self.image_files = sorted([
            f for f in os.listdir(data_dir)
            if f.startswith("patch_") and f.endswith(".npy")
        ]) if os.path.exists(data_dir) else []
        
        self.mask_files = sorted([
            f for f in os.listdir(data_dir)
            if f.startswith("mask_") and f.endswith(".npy")
        ]) if os.path.exists(data_dir) else []
        
        # Si pas de données séparées, utiliser les données synthétiques
        if len(self.image_files) == 0:
            self._load_synthetic()
    
    def _load_synthetic(self):
        """Charger ou générer des données synthétiques."""
        synthetic_path = os.path.join(SYNTHETIC_DIR, "synthetic_dataset.npz")
        
        if os.path.exists(synthetic_path):
            data = np.load(synthetic_path)
            self.images = data["images"]
            self.masks = data["masks"]
        else:
            # Générer à la volée
            n_samples = 100
            self.images = np.random.rand(n_samples, 3, self.patch_size, self.patch_size).astype(np.float32)
            self.masks = np.random.randint(0, 4, (n_samples, self.patch_size, self.patch_size)).astype(np.int64)
        
        self.image_files = None  # Marquer qu'on utilise les arrays en mémoire
    
    def __len__(self) -> int:
        if self.image_files is None:
            return len(self.images)
        return len(self.image_files)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.image_files is None:
            image = self.images[idx]
            mask = self.masks[idx]
        else:
            image = np.load(os.path.join(self.data_dir, self.image_files[idx]))
            mask = np.load(os.path.join(self.data_dir, self.mask_files[idx]))
        
        # Convertir en tenseurs
        image = torch.from_numpy(image.copy()).float()
        mask = torch.from_numpy(mask.copy()).long()
        
        # S'assurer que l'image est (C, H, W)
        if image.ndim == 2:
            image = image.unsqueeze(0)
        
        # Augmentations
        if self.augment:
            image, mask = self._augment(image, mask)
        
        return image, mask
    
    def _augment(
        self,
        image: torch.Tensor,
        mask: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Appliquer des augmentations aléatoires."""
        
        # Flip horizontal
        if torch.rand(1).item() > 0.5:
            image = torch.flip(image, [2])
            mask = torch.flip(mask, [1])
        
        # Flip vertical
        if torch.rand(1).item() > 0.5:
            image = torch.flip(image, [1])
            mask = torch.flip(mask, [0])
        
        # Rotation 90°
        k = torch.randint(0, 4, (1,)).item()
        if k > 0:
            image = torch.rot90(image, k, [1, 2])
            mask = torch.rot90(mask, k, [0, 1])
        
        # Ajustement de luminosité
        if torch.rand(1).item() > 0.5:
            factor = torch.empty(1).uniform_(0.8, 1.2).item()
            image = (image * factor).clamp(0, 1)
        
        # Bruit gaussien
        if torch.rand(1).item() > 0.7:
            noise = torch.randn_like(image) * 0.02
            image = (image + noise).clamp(0, 1)
        
        return image, mask


def create_dataloaders(
    data_dir: str = PROCESSED_DIR,
    batch_size: int = UNET_CONFIG["batch_size"],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Créer les DataLoaders pour train/val/test.
    
    Returns:
        (train_loader, val_loader, test_loader)
    """
    dataset = SatelliteDataset(data_dir, augment=False)
    
    n_total = len(dataset)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val
    
    train_set, val_set, test_set = random_split(
        dataset, [n_train, n_val, n_test],
        generator=torch.Generator().manual_seed(42)
    )
    
    # Activer l'augmentation pour le set d'entraînement
    train_dataset_aug = SatelliteDataset(data_dir, augment=True)
    train_set_aug = torch.utils.data.Subset(train_dataset_aug, train_set.indices)
    
    train_loader = DataLoader(
        train_set_aug, batch_size=batch_size, shuffle=True, num_workers=num_workers,
        pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_set, batch_size=batch_size, shuffle=False, num_workers=num_workers,
        pin_memory=True,
    )
    test_loader = DataLoader(
        test_set, batch_size=batch_size, shuffle=False, num_workers=num_workers,
        pin_memory=True,
    )
    
    print(f"📊 Dataset: {n_train} train / {n_val} val / {n_test} test")
    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    print("=== Test Dataset ===")
    
    dataset = SatelliteDataset(augment=True)
    print(f"Dataset size: {len(dataset)}")
    
    image, mask = dataset[0]
    print(f"Image shape: {image.shape}")
    print(f"Mask shape: {mask.shape}")
    print(f"Mask values: {torch.unique(mask)}")
    
    train_loader, val_loader, test_loader = create_dataloaders()
    batch = next(iter(train_loader))
    print(f"Batch images: {batch[0].shape}")
    print(f"Batch masks: {batch[1].shape}")
    print("✅ Test dataset réussi")
