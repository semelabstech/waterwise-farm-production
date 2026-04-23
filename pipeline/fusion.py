"""
F6 : Moteur de fusion intelligent — Système de décision d'irrigation.

Combine trois sources :
1. Carte de stress actuelle (U-Net / ViT)
2. Prévision météo 48h (Informer / LSTM)
3. Humidité du sol (Capteurs IoT)

Produit des recommandations d'irrigation ciblées par zone.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    FUSION_WEIGHTS, IRRIGATION_THRESHOLDS, IRRIGATION_VOLUMES,
    STRESS_LABELS, STRESS_COLORS
)


class IrrigationDecisionEngine:
    """
    Moteur de décision pour l'irrigation de précision.
    
    Algorithme de fusion pondérée :
    Score = w1 × stress_satellite + w2 × deficit_predit + w3 × (1 - humidite_sol_norm)
    """
    
    def __init__(self, weights: Optional[Dict] = None):
        self.weights = weights or FUSION_WEIGHTS
    
    def compute_irrigation_score(
        self,
        stress_level: float,
        predicted_et0: float,
        soil_moisture: float,
        et0_baseline: float = 5.0,
        moisture_field_capacity: float = 80.0,
    ) -> float:
        """
        Calculer le score d'irrigation pour une zone.
        
        Args:
            stress_level: Niveau de stress satellite (0–3) normalisé à [0, 1]
            predicted_et0: ET0 prédit à 48h (mm/jour)
            soil_moisture: Humidité du sol mesurée (% volumétrique)
            et0_baseline: ET0 de référence pour normalisation
            moisture_field_capacity: Capacité au champ du sol (%)
            
        Returns:
            Score d'irrigation [0, 1]
        """
        # Normaliser le stress satellite [0, 1]
        stress_norm = min(stress_level / 3.0, 1.0)
        
        # Normaliser le déficit prédit [0, 1]
        deficit_norm = min(predicted_et0 / et0_baseline, 1.0)
        
        # Normaliser l'humidité du sol [0, 1] (inversé : faible humidité = besoin élevé)
        moisture_norm = 1.0 - min(soil_moisture / moisture_field_capacity, 1.0)
        
        # Fusion pondérée
        score = (
            self.weights["satellite_stress"] * stress_norm
            + self.weights["weather_prediction"] * deficit_norm
            + self.weights["iot_humidity"] * moisture_norm
        )
        
        return round(min(max(score, 0), 1), 4)
    
    def get_recommendation(self, score: float) -> Dict:
        """
        Convertir un score en recommandation d'irrigation concrète.
        
        Returns:
            Dict avec priorité, action, volume d'eau
        """
        if score < IRRIGATION_THRESHOLDS["none"]:
            priority = "Basse"
            action = "Pas d'irrigation nécessaire"
            volume_range = IRRIGATION_VOLUMES["none"]
            color = "#2E7D32"
        elif score < IRRIGATION_THRESHOLDS["light"]:
            priority = "Moyenne"
            action = "Irrigation légère recommandée"
            volume_range = IRRIGATION_VOLUMES["light"]
            color = "#F9A825"
        elif score < IRRIGATION_THRESHOLDS["standard"]:
            priority = "Haute"
            action = "Irrigation standard requise"
            volume_range = IRRIGATION_VOLUMES["standard"]
            color = "#EF6C00"
        else:
            priority = "Urgente"
            action = "Irrigation intensive urgente"
            volume_range = IRRIGATION_VOLUMES["intensive"]
            color = "#C62828"
        
        volume = round((volume_range[0] + volume_range[1]) / 2, 1)
        
        return {
            "score": score,
            "priority": priority,
            "action": action,
            "volume_min_mm": volume_range[0],
            "volume_max_mm": volume_range[1],
            "volume_recommended_mm": volume,
            "color": color,
        }
    
    def analyze_zones(
        self,
        stress_map: np.ndarray,
        et0_predictions: np.ndarray,
        soil_moisture_map: np.ndarray,
        zone_size: int = 64,
    ) -> pd.DataFrame:
        """
        Analyser toutes les zones d'une parcelle et produire des recommandations.
        
        Args:
            stress_map: Carte de stress (H, W) valeurs 0–3
            et0_predictions: Prévisions ET0 par zone (mm/jour)
            soil_moisture_map: Carte d'humidité du sol (H, W) en %
            zone_size: Taille d'une zone en pixels
            
        Returns:
            DataFrame avec une recommandation par zone
        """
        h, w = stress_map.shape
        zones = []
        zone_id = 0
        
        for y in range(0, h - zone_size + 1, zone_size):
            for x in range(0, w - zone_size + 1, zone_size):
                zone_stress = stress_map[y:y+zone_size, x:x+zone_size]
                zone_moisture = soil_moisture_map[y:y+zone_size, x:x+zone_size]
                
                avg_stress = float(zone_stress.mean())
                avg_moisture = float(zone_moisture.mean())
                
                # ET0 prédit (utiliser la moyenne ou l'index)
                et0_idx = min(zone_id, len(et0_predictions) - 1)
                et0 = float(et0_predictions[et0_idx]) if len(et0_predictions) > 0 else 4.0
                
                score = self.compute_irrigation_score(avg_stress, et0, avg_moisture)
                rec = self.get_recommendation(score)
                
                zones.append({
                    "zone_id": f"Z{zone_id+1:03d}",
                    "row": y // zone_size,
                    "col": x // zone_size,
                    "x_start": x,
                    "y_start": y,
                    "stress_mean": round(avg_stress, 2),
                    "stress_label": STRESS_LABELS.get(round(avg_stress), "Inconnu"),
                    "et0_predicted": round(et0, 2),
                    "soil_moisture": round(avg_moisture, 1),
                    **rec,
                })
                zone_id += 1
        
        df = pd.DataFrame(zones)
        return df
    
    def compute_water_savings(
        self,
        recommendations: pd.DataFrame,
        uniform_volume: float = 30.0,
    ) -> Dict:
        """
        Calculer les économies d'eau par rapport à l'irrigation uniforme.
        
        Args:
            recommendations: DataFrame de recommandations
            uniform_volume: Volume d'eau uniforme habituel (mm)
            
        Returns:
            Statistiques d'économie
        """
        n_zones = len(recommendations)
        
        # Eau totale avec irrigation uniforme
        total_uniform = uniform_volume * n_zones
        
        # Eau totale avec irrigation de précision
        total_precision = recommendations["volume_recommended_mm"].sum()
        
        # Économie
        savings = total_uniform - total_precision
        savings_pct = (savings / total_uniform * 100) if total_uniform > 0 else 0
        
        return {
            "n_zones": n_zones,
            "total_uniform_mm": round(total_uniform, 1),
            "total_precision_mm": round(total_precision, 1),
            "savings_mm": round(savings, 1),
            "savings_percent": round(savings_pct, 1),
            "zones_no_irrigation": int((recommendations["volume_recommended_mm"] == 0).sum()),
            "zones_urgent": int((recommendations["priority"] == "Urgente").sum()),
            "zones_by_priority": recommendations["priority"].value_counts().to_dict(),
        }
    
    def generate_schedule(
        self,
        recommendations: pd.DataFrame,
        start_hour: int = 5,
        end_hour: int = 8,
    ) -> pd.DataFrame:
        """
        Générer un planning d'irrigation optimisé.
        Irrigue aux heures fraîches (tôt le matin) par ordre de priorité.
        """
        priority_order = {"Urgente": 0, "Haute": 1, "Moyenne": 2, "Basse": 3}
        
        # Filtrer les zones nécessitant de l'irrigation
        to_irrigate = recommendations[recommendations["volume_recommended_mm"] > 0].copy()
        to_irrigate["priority_rank"] = to_irrigate["priority"].map(priority_order)
        to_irrigate = to_irrigate.sort_values("priority_rank")
        
        # Assigner les heures
        schedule = []
        current_hour = start_hour
        current_minute = 0
        
        for _, zone in to_irrigate.iterrows():
            # Durée proportionnelle au volume (environ 10 min par 10mm)
            duration_min = max(10, int(zone["volume_recommended_mm"] / 10 * 10))
            
            schedule.append({
                "zone_id": zone["zone_id"],
                "start_time": f"{current_hour:02d}:{current_minute:02d}",
                "duration_min": duration_min,
                "volume_mm": zone["volume_recommended_mm"],
                "priority": zone["priority"],
            })
            
            current_minute += duration_min
            while current_minute >= 60:
                current_minute -= 60
                current_hour += 1
            
            if current_hour >= end_hour:
                break
        
        return pd.DataFrame(schedule)


if __name__ == "__main__":
    print("=== Test Fusion Engine ===")
    
    engine = IrrigationDecisionEngine()
    
    # Test individual score
    score = engine.compute_irrigation_score(
        stress_level=2.5,   # Stress modéré-sévère
        predicted_et0=6.0,  # ET0 élevé
        soil_moisture=25.0  # Humidité faible
    )
    rec = engine.get_recommendation(score)
    print(f"Score: {score} → {rec['action']} ({rec['volume_recommended_mm']} mm)")
    
    # Test zone analysis
    h, w = 256, 256
    stress_map = np.random.randint(0, 4, (h, w)).astype(np.float32)
    et0_predictions = np.random.uniform(3, 7, 16)
    moisture_map = np.random.uniform(15, 70, (h, w))
    
    recommendations = engine.analyze_zones(stress_map, et0_predictions, moisture_map)
    savings = engine.compute_water_savings(recommendations)
    schedule = engine.generate_schedule(recommendations)
    
    print(f"\n📊 {len(recommendations)} zones analysées")
    print(f"💧 Économie d'eau: {savings['savings_percent']:.1f}%")
    print(f"\n📋 Planning d'irrigation:")
    print(schedule.head(10))
    print("✅ Test fusion réussi")
