"""
Training script for Crop Water MLP model.
Generates synthetic training data from FAO-56 crop database x climate profiles.
"""
import os, sys, json
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import TensorDataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models.crop_water.model import CropWaterMLP
from config.settings import DATA_DIR

CROP_DB_PATH = os.path.join(DATA_DIR, "crops", "fao_crop_database.json")
MODEL_SAVE_DIR = os.path.join(DATA_DIR, "crops", "models")

# Climate profiles for worldwide diversity
CLIMATE_ZONES = [
    {"name": "Tropical Humid", "temp": 28, "humidity": 80, "solar": 18, "wind": 2.0, "et0_base": 4.5},
    {"name": "Tropical Dry", "temp": 32, "humidity": 45, "solar": 22, "wind": 3.0, "et0_base": 6.5},
    {"name": "Arid Hot", "temp": 36, "humidity": 20, "solar": 25, "wind": 3.5, "et0_base": 8.0},
    {"name": "Arid Cold", "temp": 18, "humidity": 30, "solar": 20, "wind": 4.0, "et0_base": 5.5},
    {"name": "Mediterranean", "temp": 22, "humidity": 55, "solar": 20, "wind": 2.5, "et0_base": 5.0},
    {"name": "Subtropical Humid", "temp": 25, "humidity": 70, "solar": 17, "wind": 2.0, "et0_base": 4.0},
    {"name": "Oceanic", "temp": 14, "humidity": 75, "solar": 12, "wind": 3.5, "et0_base": 2.5},
    {"name": "Continental Warm", "temp": 20, "humidity": 50, "solar": 18, "wind": 3.0, "et0_base": 4.5},
    {"name": "Continental Cold", "temp": 8, "humidity": 60, "solar": 12, "wind": 3.5, "et0_base": 2.0},
    {"name": "Monsoon", "temp": 27, "humidity": 85, "solar": 15, "wind": 2.0, "et0_base": 3.5},
    {"name": "Saharan", "temp": 40, "humidity": 15, "solar": 27, "wind": 4.0, "et0_base": 9.0},
    {"name": "Highland Tropical", "temp": 18, "humidity": 65, "solar": 18, "wind": 2.5, "et0_base": 3.5},
]

SOIL_TYPES = [
    {"name": "Sandy", "factor": 0.85},
    {"name": "Loamy", "factor": 1.0},
    {"name": "Clay", "factor": 1.1},
    {"name": "Silt", "factor": 0.95},
    {"name": "Alluvial", "factor": 1.05},
    {"name": "Calcaire", "factor": 0.9},
]


def get_kc_at_day(crop, day):
    """Interpolate Kc value at a given day of the growth cycle."""
    stages = crop["stage_days"]
    d_ini = stages["initial"]
    d_dev = stages["development"]
    d_mid = stages["mid"]
    d_late = stages["late"]

    if day <= d_ini:
        return crop["kc_ini"]
    elif day <= d_ini + d_dev:
        frac = (day - d_ini) / d_dev
        return crop["kc_ini"] + frac * (crop["kc_mid"] - crop["kc_ini"])
    elif day <= d_ini + d_dev + d_mid:
        return crop["kc_mid"]
    else:
        elapsed = day - (d_ini + d_dev + d_mid)
        frac = min(elapsed / d_late, 1.0)
        return crop["kc_mid"] + frac * (crop["kc_end"] - crop["kc_mid"])


def generate_training_data():
    """Generate synthetic training data: crops x climates x days x soils."""
    with open(CROP_DB_PATH, "r", encoding="utf-8") as f:
        crops = json.load(f)

    rng = np.random.RandomState(42)
    X_all, y_all = [], []

    for crop in crops:
        total_days = crop["total_growing_days"]
        for climate in CLIMATE_ZONES:
            for soil_idx, soil in enumerate(SOIL_TYPES):
                for day in range(1, total_days + 1, 3):  # Every 3rd day
                    kc = get_kc_at_day(crop, day)
                    growth_frac = day / total_days

                    # Seasonal variation
                    seasonal = np.sin(2 * np.pi * day / 365)
                    temp = climate["temp"] + 5 * seasonal + rng.normal(0, 2)
                    humidity = np.clip(climate["humidity"] + 10 * seasonal + rng.normal(0, 5), 10, 95)
                    wind = np.clip(climate["wind"] + rng.normal(0, 0.5), 0.3, 8)
                    solar = np.clip(climate["solar"] + 3 * seasonal + rng.normal(0, 1.5), 4, 30)
                    et0 = np.clip(climate["et0_base"] + 2 * seasonal + rng.normal(0, 0.5), 0.5, 12)

                    # Target: ETc = Kc * ET0 * soil_factor + corrections
                    etc_base = kc * et0 * soil["factor"]
                    # Corrections: high wind +5%, low humidity +8%, high temp +3%
                    wind_corr = 1.0 + 0.02 * max(wind - 3, 0)
                    humid_corr = 1.0 + 0.002 * max(50 - humidity, 0)
                    temp_corr = 1.0 + 0.005 * max(temp - 30, 0)
                    etc_target = etc_base * wind_corr * humid_corr * temp_corr
                    etc_target += rng.normal(0, 0.1)  # Noise
                    etc_target = max(0.05, etc_target)

                    X_all.append([kc, et0, temp, humidity, wind, solar, soil_idx, growth_frac])
                    y_all.append(etc_target)

    X = np.array(X_all, dtype=np.float32)
    y = np.array(y_all, dtype=np.float32)
    print(f"    Generated {len(X):,} training samples from {len(crops)} crops x {len(CLIMATE_ZONES)} climates x {len(SOIL_TYPES)} soils")
    return X, y


def train_crop_water_model():
    print("=" * 60)
    print("  Training Crop Water MLP (ETc Prediction)")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"    Device: {device}")

    X, y = generate_training_data()

    # Normalize
    X_mean, X_std = X.mean(axis=0), X.std(axis=0)
    X_norm = (X - X_mean) / (X_std + 1e-8)
    y_mean, y_std = y.mean(), y.std()
    y_norm = (y - y_mean) / (y_std + 1e-8)

    # Split
    split = int(0.85 * len(X))
    train_ds = TensorDataset(torch.tensor(X_norm[:split]), torch.tensor(y_norm[:split]))
    val_ds = TensorDataset(torch.tensor(X_norm[split:]), torch.tensor(y_norm[split:]))
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False)

    model = CropWaterMLP(input_dim=8).to(device)
    optimizer = AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
    criterion = nn.MSELoss()

    best_val = float("inf")
    epochs = 30

    for epoch in range(1, epochs + 1):
        model.train()
        t_loss = 0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            optimizer.step()
            t_loss += loss.item()

        model.eval()
        v_loss = 0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                pred = model(bx)
                v_loss += criterion(pred, by).item()

        t_avg = t_loss / len(train_loader)
        v_avg = v_loss / len(val_loader)
        print(f"  Epoch {epoch:02d}/{epochs} | Train: {t_avg:.4f} | Val: {v_avg:.4f}")

        if v_avg < best_val:
            best_val = v_avg
            os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "X_mean": X_mean, "X_std": X_std,
                "y_mean": y_mean, "y_std": y_std,
            }, os.path.join(MODEL_SAVE_DIR, "crop_water_mlp.pth"))

    print(f"\n    Model saved. Best validation loss: {best_val:.4f}")


if __name__ == "__main__":
    train_crop_water_model()
