import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import TensorDataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.weather import generate_synthetic_weather
from pipeline.iot import IoTSimulator
from models.iot.model import IoTAnomalyDetector
from config.settings import IOT_DIR

def prepare_data(seq_len=12):
    print("📡 Generating synthetic training data for IoT...")
    weather_df = generate_synthetic_weather(365) # 1 year of data
    simulator = IoTSimulator(num_sensors=1)      # Single generic sensor pattern
    
    # generate_readings gets 60 min intervals if configured so, usually 24 reads a day maybe
    readings = simulator.generate_readings(weather_df, interval_minutes=60)
    
    # Merge weather data into readings (weather is daily, readings are hourly)
    readings["date_str"] = readings["timestamp"].dt.date.astype(str)
    weather_df["date_str"] = weather_df["date"].dt.date.astype(str)
    
    merged = pd.merge(readings, weather_df, on="date_str", how="left")
    
    features = ["soil_moisture", "temperature", "humidity", "precipitation"]
    data = merged[features].values
    
    # Normalize features
    scaler_mean = data.mean(axis=0)
    scaler_std = data.std(axis=0)
    data_norm = (data - scaler_mean) / (scaler_std + 1e-8)
    
    # Create sequences
    X = []
    for i in range(len(data_norm) - seq_len):
        X.append(data_norm[i : i + seq_len])
    X = np.array(X, dtype=np.float32)
    
    return X, scaler_mean, scaler_std

def train_iot_model():
    print("=" * 60)
    print("  === Entraînement Modèle IoT (Anomaly Detection) ===")
    print("=" * 60)
    
    seq_len = 12
    batch_size = 64
    epochs = 20
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    X, scaler_mean, scaler_std = prepare_data(seq_len=seq_len)
    
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train)), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_val)), batch_size=batch_size, shuffle=False)
    
    model = IoTAnomalyDetector(input_dim=4).to(device)
    optimizer = AdamW(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    best_loss = float('inf')
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0
        for (batch_x,) in train_loader:
            batch_x = batch_x.to(device)
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for (batch_x,) in val_loader:
                batch_x = batch_x.to(device)
                recon = model(batch_x)
                loss = criterion(recon, batch_x)
                val_loss += loss.item()
                
        t_loss = train_loss / len(train_loader)
        v_loss = val_loss / len(val_loader)
        
        print(f"Epoch {epoch:02d} | Train Loss: {t_loss:.4f} | Val Loss: {v_loss:.4f}")
        
        if v_loss < best_loss:
            best_loss = v_loss
            os.makedirs(os.path.join(IOT_DIR, "models"), exist_ok=True)
            save_path = os.path.join(IOT_DIR, "models", "iot_autoencoder.pth")
            torch.save({
                "model_state_dict": model.state_dict(),
                "scaler_mean": scaler_mean,
                "scaler_std": scaler_std,
                "seq_len": seq_len,
                "val_threshold": best_loss * 2.5 # Threshold = 2.5x mean val loss
            }, save_path)
            
    print(f"\n✅ Modèle sauvegardé dans {save_path}")
    print(f"Threshold pour anomalies : {best_loss * 2.5:.4f}")

if __name__ == "__main__":
    train_iot_model()
