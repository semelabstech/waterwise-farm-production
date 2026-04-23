"""
Acquisition de données météorologiques.

Sources :
- NASA POWER API (données historiques et prévisionnelles)
- Open-Meteo API (gratuit, sans clé)

Calcul de l'évapotranspiration de référence ET0 (FAO Penman-Monteith).
"""
import os
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import NASA_POWER_API_URL, OPEN_METEO_API_URL, WEATHER_DIR, DEFAULT_CENTER


class WeatherFetcher:
    """
    Récupérer les données météorologiques depuis des API gratuites.
    """
    
    def __init__(self, lat: float = None, lon: float = None):
        self.lat = lat or DEFAULT_CENTER["lat"]
        self.lon = lon or DEFAULT_CENTER["lon"]
        self.cache_dir = WEATHER_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_nasa_power(
        self,
        start_date: str = "20240101",
        end_date: str = "20241231",
        parameters: str = "T2M,RH2M,WS2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
    ) -> Optional[pd.DataFrame]:
        """
        Récupérer les données depuis NASA POWER API.
        
        Paramètres disponibles :
        - T2M : Température à 2m (°C)
        - RH2M : Humidité relative à 2m (%)
        - WS2M : Vitesse du vent à 2m (m/s)
        - PRECTOTCORR : Précipitations corrigées (mm/jour)
        - ALLSKY_SFC_SW_DWN : Radiation solaire (MJ/m²/jour)
        """
        cache_file = os.path.join(
            self.cache_dir,
            f"nasa_power_{self.lat}_{self.lon}_{start_date}_{end_date}.csv"
        )
        
        # Vérifier le cache
        if os.path.exists(cache_file):
            print(f"📁 Données météo en cache: {cache_file}")
            return pd.read_csv(cache_file, parse_dates=["date"])
        
        try:
            response = requests.get(
                NASA_POWER_API_URL,
                params={
                    "parameters": parameters,
                    "community": "AG",
                    "longitude": self.lon,
                    "latitude": self.lat,
                    "start": start_date,
                    "end": end_date,
                    "format": "JSON",
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            # Parser les données
            properties = data.get("properties", {}).get("parameter", {})
            if not properties:
                print("⚠️  Pas de données dans la réponse NASA POWER.")
                return None
            
            df = pd.DataFrame(properties)
            df.index.name = "date"
            df.index = pd.to_datetime(df.index, format="%Y%m%d")
            df = df.reset_index()
            
            # Renommer les colonnes
            col_map = {
                "T2M": "temperature",
                "RH2M": "humidity",
                "WS2M": "wind_speed",
                "PRECTOTCORR": "precipitation",
                "ALLSKY_SFC_SW_DWN": "solar_radiation",
            }
            df = df.rename(columns=col_map)
            
            # Remplacer les valeurs manquantes (-999)
            df = df.replace(-999, np.nan)
            df = df.interpolate(method="linear")
            
            # Sauvegarder en cache
            df.to_csv(cache_file, index=False)
            print(f"✅ {len(df)} jours de données météo récupérés (NASA POWER).")
            return df
            
        except Exception as e:
            print(f"⚠️  Erreur NASA POWER: {e}. Tentative Open-Meteo...")
            return self.fetch_open_meteo(start_date, end_date)
    
    def fetch_open_meteo(
        self,
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
    ) -> Optional[pd.DataFrame]:
        """
        Récupérer les données depuis Open-Meteo API (gratuit, sans clé).
        """
        # Formatter les dates
        if len(start_date) == 8:
            start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        if len(end_date) == 8:
            end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        cache_file = os.path.join(
            self.cache_dir,
            f"open_meteo_{self.lat}_{self.lon}_{start_date}_{end_date}.csv"
        )
        
        if os.path.exists(cache_file):
            print(f"📁 Données météo en cache: {cache_file}")
            return pd.read_csv(cache_file, parse_dates=["date"])
        
        try:
            response = requests.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": self.lat,
                    "longitude": self.lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": "temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_max,precipitation_sum,shortwave_radiation_sum",
                    "timezone": "auto",
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            daily = data.get("daily", {})
            df = pd.DataFrame({
                "date": pd.to_datetime(daily["time"]),
                "temperature": daily["temperature_2m_mean"],
                "humidity": daily["relative_humidity_2m_mean"],
                "wind_speed": daily["wind_speed_10m_max"],
                "precipitation": daily["precipitation_sum"],
                "solar_radiation": [
                    x / 1000 if x else 0 for x in daily["shortwave_radiation_sum"]
                ],  # kJ/m² → MJ/m²
            })
            
            df = df.interpolate(method="linear")
            df.to_csv(cache_file, index=False)
            print(f"✅ {len(df)} jours de données météo récupérés (Open-Meteo).")
            return df
            
        except Exception as e:
            print(f"❌ Erreur Open-Meteo: {e}")
            return None
    
    def compute_et0(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculer l'évapotranspiration de référence ET0 (FAO Penman-Monteith simplifiée).
        
        ET0 = 0.0023 * (T_mean + 17.8) * (T_max - T_min)^0.5 * Ra
        (Méthode Hargreaves simplifiée quand les données complètes ne sont pas disponibles)
        
        Pour la version complète, utilise la formule FAO-56 :
        ET0 = (0.408 * Δ * Rn + γ * 900/(T+273) * u2 * (es - ea)) / (Δ + γ * (1 + 0.34*u2))
        """
        df = df.copy()
        
        T = df["temperature"].values  # °C
        RH = df["humidity"].values    # %
        u2 = df["wind_speed"].values  # m/s
        Rs = df["solar_radiation"].values  # MJ/m²/jour
        
        # Pression de vapeur saturée (kPa)
        es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
        
        # Pression de vapeur réelle (kPa)
        ea = es * RH / 100.0
        
        # Pente de la courbe de pression de vapeur (kPa/°C)
        delta = 4098 * es / (T + 237.3) ** 2
        
        # Constante psychrométrique (kPa/°C) — approximation à 101.3 kPa
        gamma = 0.0665
        
        # Radiation nette (approximation)
        Rn = 0.77 * Rs  # Radiation nette ≈ 77% de la radiation courte
        
        # ET0 FAO-56 Penman-Monteith
        numerator = 0.408 * delta * Rn + gamma * (900 / (T + 273)) * u2 * (es - ea)
        denominator = delta + gamma * (1 + 0.34 * u2)
        
        et0 = numerator / denominator
        et0 = np.maximum(et0, 0)  # ET0 ne peut pas être négatif
        
        df["et0"] = et0.round(3)
        
        print(f"[ET0] range: [{df['et0'].min():.2f}, {df['et0'].max():.2f}] mm/jour")
        return df


def generate_synthetic_weather(
    n_days: int = 365,
    start_date: str = "2024-01-01",
    lat: float = 30.5,
) -> pd.DataFrame:
    """
    Générer des données météo synthétiques réalistes pour le Maroc.
    Utile pour le mode démo.
    """
    dates = pd.date_range(start=start_date, periods=n_days, freq="D")
    
    # Jour de l'année pour la saisonnalité
    doy = dates.dayofyear.values
    seasonal = np.sin(2 * np.pi * (doy - 80) / 365)  # Max en été
    
    # Température (°C) — Maroc semi-aride
    temp_base = 20 + 12 * seasonal
    temperature = temp_base + np.random.normal(0, 2, n_days)
    
    # Humidité relative (%) — inverse de la température
    humidity = 55 - 20 * seasonal + np.random.normal(0, 8, n_days)
    humidity = np.clip(humidity, 15, 95)
    
    # Vent (m/s)
    wind = 3 + 1.5 * np.abs(seasonal) + np.random.exponential(0.5, n_days)
    
    # Précipitations (mm/jour) — principalement en hiver
    precip_prob = 0.15 * (1 - seasonal * 0.7)  # Plus de pluie en hiver
    precip = np.where(
        np.random.random(n_days) < precip_prob,
        np.random.exponential(8, n_days),
        0
    )
    
    # Radiation solaire (MJ/m²/jour)
    solar = 15 + 8 * seasonal + np.random.normal(0, 1.5, n_days)
    solar = np.clip(solar, 3, 30)
    
    df = pd.DataFrame({
        "date": dates,
        "temperature": temperature.round(1),
        "humidity": humidity.round(1),
        "wind_speed": wind.round(2),
        "precipitation": precip.round(1),
        "solar_radiation": solar.round(2),
    })
    
    return df


if __name__ == "__main__":
    print("=== Test Weather Pipeline ===")
    
    # Générer des données synthétiques
    df = generate_synthetic_weather(365)
    print(f"📅 {len(df)} jours générés")
    print(df.describe())
    
    # Calculer ET0
    fetcher = WeatherFetcher()
    df = fetcher.compute_et0(df)
    print(f"\n📊 ET0 moyen: {df['et0'].mean():.2f} mm/jour")
    print("✅ Test météo réussi")
