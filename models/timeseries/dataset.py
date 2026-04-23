"""
Dataset PyTorch pour les séries temporelles météorologiques.

Format des données :
- Input : 14 jours de [temperature, humidity, wind_speed, precipitation, solar_radiation]
- Target : ET0 à 24h et 48h
"""
import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.preprocessing import StandardScaler
from typing import Optional, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import TIMESERIES_CONFIG, WEATHER_DIR, SYNTHETIC_DIR


class WeatherTimeSeriesDataset(Dataset):
    """
    Dataset de séries temporelles météo pour la prévision ET0.
    
    Utilise une fenêtre glissante de 14 jours en entrée
    pour prédire ET0 à 24h et 48h.
    """
    
    def __init__(
        self,
        data: Optional[pd.DataFrame] = None,
        input_days: int = TIMESERIES_CONFIG["input_days"],
        features: list = None,
        target_col: str = "et0",
        normalize: bool = True,
    ):
        self.input_days = input_days
        self.features = features or TIMESERIES_CONFIG["features"]
        self.target_col = target_col
        
        if data is not None:
            self.df = data
        else:
            self.df = self._load_or_generate()
        
        # S'assurer que les colonnes existent
        missing = [f for f in self.features if f not in self.df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes: {missing}")
        
        if self.target_col not in self.df.columns:
            raise ValueError(f"Colonne cible '{self.target_col}' manquante. Calculer ET0 d'abord.")
        
        # Normalisation
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        
        X_values = self.df[self.features].values
        y_values = self.df[self.target_col].values.reshape(-1, 1)
        
        if normalize:
            self.X = self.scaler_X.fit_transform(X_values)
            self.y = self.scaler_y.fit_transform(y_values).flatten()
        else:
            self.X = X_values
            self.y = y_values.flatten()
        
        # Créer les séquences
        self.sequences = []
        for i in range(len(self.X) - input_days - 2):  # -2 pour les targets à +1 et +2 jours
            seq_x = self.X[i:i + input_days]
            target_24h = self.y[i + input_days]       # ET0 à +1 jour (24h)
            target_48h = self.y[i + input_days + 1]   # ET0 à +2 jours (48h)
            self.sequences.append((seq_x, np.array([target_24h, target_48h])))
    
    def _load_or_generate(self) -> pd.DataFrame:
        """Charger ou générer des données."""
        # Chercher des données existantes
        for f in os.listdir(WEATHER_DIR) if os.path.exists(WEATHER_DIR) else []:
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(WEATHER_DIR, f), parse_dates=["date"])
                if "et0" in df.columns:
                    return df
        
        # Générer des données synthétiques
        print("⚠️  Pas de données météo trouvées. Génération synthétique...")
        from pipeline.weather import generate_synthetic_weather, WeatherFetcher
        df = generate_synthetic_weather(365)
        fetcher = WeatherFetcher()
        df = fetcher.compute_et0(df)
        return df
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        x, y = self.sequences[idx]
        return (
            torch.from_numpy(x.copy()).float(),
            torch.from_numpy(y.copy()).float(),
        )
    
    def inverse_transform_y(self, y: np.ndarray) -> np.ndarray:
        """Dénormaliser les prédictions."""
        return self.scaler_y.inverse_transform(y.reshape(-1, 1)).flatten()
    
    def get_scalers(self):
        """Retourner les scalers pour usage externe."""
        return self.scaler_X, self.scaler_y


def create_timeseries_dataloaders(
    data: Optional[pd.DataFrame] = None,
    batch_size: int = TIMESERIES_CONFIG["batch_size"],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader, WeatherTimeSeriesDataset]:
    """
    Créer les DataLoaders avec split temporel.
    
    Note : Pour les séries temporelles, on fait un split séquentiel
    (pas aléatoire) pour respecter la causalité.
    
    Returns:
        (train_loader, val_loader, test_loader, dataset)
    """
    dataset = WeatherTimeSeriesDataset(data=data)
    
    n_total = len(dataset)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val
    
    # Split séquentiel (pas aléatoire !)
    train_set = torch.utils.data.Subset(dataset, range(0, n_train))
    val_set = torch.utils.data.Subset(dataset, range(n_train, n_train + n_val))
    test_set = torch.utils.data.Subset(dataset, range(n_train + n_val, n_total))
    
    train_loader = DataLoader(
        train_set, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True,
    )
    val_loader = DataLoader(
        val_set, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )
    test_loader = DataLoader(
        test_set, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )
    
    print(f"📊 Time-series Dataset: {n_train} train / {n_val} val / {n_test} test")
    return train_loader, val_loader, test_loader, dataset


if __name__ == "__main__":
    print("=== Test Time-Series Dataset ===")
    
    dataset = WeatherTimeSeriesDataset()
    print(f"Dataset size: {len(dataset)}")
    
    x, y = dataset[0]
    print(f"Input shape: {x.shape} (14 jours × 5 features)")
    print(f"Target shape: {y.shape} (ET0 24h, ET0 48h)")
    
    train_loader, val_loader, test_loader, _ = create_timeseries_dataloaders()
    batch_x, batch_y = next(iter(train_loader))
    print(f"Batch X: {batch_x.shape}")
    print(f"Batch Y: {batch_y.shape}")
    print("✅ Test dataset séries temporelles réussi")
