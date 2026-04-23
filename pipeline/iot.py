"""
F5 : Intégration des capteurs IoT d'humidité du sol.

Ce module fournit :
- Un simulateur de capteurs IoT réalistes
- Un ingestion de données réelles (CSV / MQTT)
- Interpolation et nettoyage des données
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import IOT_DIR, IOT_CONFIG, DEFAULT_CENTER


class IoTSimulator:
    """
    Simulateur de capteurs d'humidité du sol.
    
    Génère des données réalistes corrélées avec la météo :
    - L'humidité augmente après la pluie
    - L'humidité diminue avec la température et le vent
    - Bruit gaussien pour simuler l'imprécision des capteurs
    """
    
    def __init__(
        self,
        num_sensors: int = IOT_CONFIG["num_sensors"],
        center_lat: float = None,
        center_lon: float = None,
        spread: float = 0.05,  # Dispersion GPS en degrés
    ):
        self.num_sensors = num_sensors
        self.center_lat = center_lat or DEFAULT_CENTER["lat"]
        self.center_lon = center_lon or DEFAULT_CENTER["lon"]
        self.spread = spread
        
        # Générer les positions des capteurs
        np.random.seed(42)
        self.sensors = []
        for i in range(num_sensors):
            self.sensors.append({
                "sensor_id": f"SENSOR_{i+1:03d}",
                "latitude": self.center_lat + np.random.uniform(-spread, spread),
                "longitude": self.center_lon + np.random.uniform(-spread, spread),
                "depth_cm": np.random.choice([10, 20, 30]),
            })
    
    def generate_readings(
        self,
        weather_df: pd.DataFrame,
        interval_minutes: int = IOT_CONFIG["reading_interval_minutes"],
    ) -> pd.DataFrame:
        """
        Générer des lectures de capteurs corrélées avec la météo.
        
        Args:
            weather_df: DataFrame avec colonnes [date, temperature, humidity, precipitation]
            interval_minutes: Intervalle entre les lectures
            
        Returns:
            DataFrame avec toutes les lectures IoT
        """
        all_readings = []
        
        for sensor in self.sensors:
            # Humidité de base du sol (dépend de la position)
            base_moisture = np.random.uniform(30, 50)
            
            for _, day in weather_df.iterrows():
                date = pd.to_datetime(day["date"])
                n_readings = 24 * 60 // interval_minutes
                
                for r in range(n_readings):
                    timestamp = date + timedelta(minutes=r * interval_minutes)
                    
                    # Heure du jour influence
                    hour = timestamp.hour
                    diurnal_effect = -2 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 1
                    
                    # Effet de la pluie (augmente l'humidité)
                    rain_effect = min(day["precipitation"] * 2.5, 30)
                    
                    # Effet de la température (diminue l'humidité)
                    temp_effect = -0.3 * max(day["temperature"] - 25, 0)
                    
                    # Effet du vent (augmente l'évaporation)
                    wind_effect = -0.2 * day["wind_speed"]
                    
                    # Calcul de l'humidité du sol
                    moisture = (
                        base_moisture
                        + rain_effect
                        + temp_effect
                        + wind_effect
                        + diurnal_effect
                        + np.random.normal(0, IOT_CONFIG["noise_std"])
                    )
                    
                    moisture = np.clip(moisture, *IOT_CONFIG["humidity_range"])
                    
                    all_readings.append({
                        "timestamp": timestamp,
                        "sensor_id": sensor["sensor_id"],
                        "latitude": sensor["latitude"],
                        "longitude": sensor["longitude"],
                        "depth_cm": sensor["depth_cm"],
                        "soil_moisture": round(float(moisture), 1),
                    })
                
                # Ajuster la base pour le jour suivant (inertie)
                base_moisture = base_moisture * 0.95 + (
                    base_moisture + rain_effect + temp_effect
                ) * 0.05
                base_moisture = np.clip(base_moisture, 10, 80)
        
        df = pd.DataFrame(all_readings)
        print(f"    {len(df)} lectures IoT générées pour {self.num_sensors} capteurs")
        return df
    
    def generate_daily_summary(self, readings_df: pd.DataFrame) -> pd.DataFrame:
        """
        Résumer les lectures journalières par capteur.
        """
        readings_df["date"] = pd.to_datetime(readings_df["timestamp"]).dt.date
        
        summary = readings_df.groupby(["date", "sensor_id"]).agg(
            moisture_mean=("soil_moisture", "mean"),
            moisture_min=("soil_moisture", "min"),
            moisture_max=("soil_moisture", "max"),
            moisture_std=("soil_moisture", "std"),
            n_readings=("soil_moisture", "count"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
        ).reset_index()
        
        summary = summary.round(2)
        return summary


class IoTIngestion:
    """
    Gestionnaire d'ingestion de données IoT réelles.
    """
    
    @staticmethod
    def read_csv(filepath: str) -> pd.DataFrame:
        """
        Lire des données IoT depuis un fichier CSV.
        
        Colonnes attendues : timestamp, sensor_id, latitude, longitude, soil_moisture
        """
        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        
        # Nettoyage
        df = df.dropna(subset=["soil_moisture"])
        df["soil_moisture"] = df["soil_moisture"].clip(*IOT_CONFIG["humidity_range"])
        
        print(f"    {len(df)} lectures chargées depuis {filepath}")
        return df
    
    @staticmethod
    def interpolate_missing(
        df: pd.DataFrame,
        interval: str = "30min",
    ) -> pd.DataFrame:
        """
        Interpoler les lectures manquantes.
        """
        result_frames = []
        
        for sensor_id, group in df.groupby("sensor_id"):
            group = group.set_index("timestamp")
            group = group.resample(interval).mean()
            group = group.interpolate(method="linear")
            group["sensor_id"] = sensor_id
            result_frames.append(group)
        
        result = pd.concat(result_frames).reset_index()
        return result
    
    @staticmethod
    def get_current_moisture(df: pd.DataFrame) -> Dict:
        """
        Obtenir la dernière lecture de chaque capteur.
        """
        latest = df.sort_values("timestamp").groupby("sensor_id").last()
        return latest[["soil_moisture", "latitude", "longitude"]].to_dict("index")

_iot_model = None
_iot_checkpoint = None

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Utilise le modèle Autoencoder entraîné pour détecter les anomalies
    dans les lectures IoT (capteur défectueux, sécheresse inexpliquée).
    """
    global _iot_model, _iot_checkpoint
    
    try:
        import torch
        from models.iot.model import IoTAnomalyDetector

        model_path = os.path.join(IOT_DIR, "models", "iot_autoencoder.pth")
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model not trained")
            
        if _iot_model is None:
            _iot_checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
            _iot_model = IoTAnomalyDetector(input_dim=4)
            _iot_model.load_state_dict(_iot_checkpoint["model_state_dict"])
            _iot_model.eval()
        
        scaler_mean = _iot_checkpoint["scaler_mean"]
        scaler_std = _iot_checkpoint["scaler_std"]
        seq_len = _iot_checkpoint["seq_len"]
        threshold = _iot_checkpoint["val_threshold"]
        
        # S'assurer d'avoir les colonnes nécessaires
        features = ["soil_moisture", "temperature", "humidity", "precipitation"]
        
        df = df.sort_values(by=["sensor_id", "timestamp"]).copy()
        df["anomaly_score"] = 0.0
        df["is_anomaly"] = False
        
        for sensor_id, group in df.groupby("sensor_id"):
            if len(group) < seq_len:
                continue
            
            # Préparer les données
            data = group[features].values
            data_norm = (data - scaler_mean) / (scaler_std + 1e-8)
            
            # Créer les séquences
            X = []
            valid_indices = []
            for i in range(len(data_norm) - seq_len + 1):
                X.append(data_norm[i : i + seq_len])
                valid_indices.append(group.index[i + seq_len - 1])
                
            X = torch.tensor(np.array(X, dtype=np.float32))
            
            # Inférence
            with torch.no_grad():
                recon = _iot_model(X)
                # MSE par séquence
                mse = torch.mean((recon - X)**2, dim=(1, 2)).numpy()
                
            # Assigner les scores
            for idx, score in zip(valid_indices, mse):
                df.at[idx, "anomaly_score"] = float(score)
                df.at[idx, "is_anomaly"] = bool(score > threshold * 1.5) # On ajoute un petit facteur de sécurité
                
        return df
    except Exception as e:
        print(f"    Erreur lors de la détection d'anomalies : {e}")
        df["anomaly_score"] = 0.0
        df["is_anomaly"] = False
        return df

def save_iot_data(df: pd.DataFrame, filename: str = "iot_readings.csv"):
    """Sauvegarder les données IoT."""
    filepath = os.path.join(IOT_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"    Données IoT sauvegardées: {filepath}")


if __name__ == "__main__":
    print("=== Test IoT Simulator ===")
    
    # Créer des données météo minimales
    from pipeline.weather import generate_synthetic_weather
    weather = generate_synthetic_weather(7)
    
    # Simuler des capteurs
    simulator = IoTSimulator(num_sensors=3)
    readings = simulator.generate_readings(weather)
    summary = simulator.generate_daily_summary(readings)
    
    print(f"\n📊 Résumé journalier :")
    print(summary.head(10))
    print("✅ Test IoT réussi")
