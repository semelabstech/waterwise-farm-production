"""
FastAPI backend — Precision Irrigation System.
Region-aware API serving data to the React frontend.
"""
import os, sys, json, hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import threading

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from config.settings import (
    SYNTHETIC_DIR, STRESS_LABELS, STRESS_COLORS,
    DEFAULT_CENTER, DEFAULT_BBOX, FUSION_WEIGHTS,
    MOROCCO_REGIONS, MOROCCO_CENTER, MOROCCO_FULL_BBOX
)
from pipeline.fusion import IrrigationDecisionEngine
from pipeline.weather import generate_synthetic_weather, WeatherFetcher
from pipeline.iot import IoTSimulator, detect_anomalies
from pipeline.crop_planner import (
    get_crop_catalog, get_crop_by_id, get_categories,
    estimate_climate, compute_water_budget, compute_multi_crop_budget
)

# Custom regions storage for farmer mode
CUSTOM_REGIONS = {}

app = FastAPI(title="Precision Irrigation API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_json(obj):
    """Convert numpy types to JSON-safe Python types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def df_to_records(df):
    """Convert DataFrame to list of dicts with safe types."""
    records = df.to_dict(orient="records")
    cleaned = []
    for row in records:
        cleaned.append({k: safe_json(v) for k, v in row.items()})
    return cleaned


def find_nearest_region(lat: float, lon: float) -> str:
    """Find the nearest predefined region template based on Euclidean distance."""
    min_dist = float('inf')
    best_key = "souss_massa"
    for key, info in MOROCCO_REGIONS.items():
        # Only consider primary templates (keys without 'gps_')
        if not key.startswith("gps_") and "center" in info:
            c = info["center"]
            dist = ((c["lat"] - lat)**2 + (c["lon"] - lon)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                best_key = key
    return best_key

def ensure_region(region: str, lat: float = None, lon: float = None, name: str = None) -> str:
    """
    Ensure the region key is correct. If GPS coords are provided, 
    generate/fetch a custom region specifically for those coords.
    """
    if lat is not None and lon is not None:
        # Use round to stabilize keys
        lat_r = round(lat, 4)
        lon_r = round(lon, 4)
        region_key = f"gps_{lat_r}_{lon_r}"
        
        if region_key not in CUSTOM_REGIONS:
            # First, try to find a matching BBOX for high precision
            template_key = None
            for key, info in MOROCCO_REGIONS.items():
                if not key.startswith("gps_") and "bbox" in info:
                    b = info["bbox"]
                    if b["south"] <= lat <= b["north"] and b["west"] <= lon <= b["east"]:
                        template_key = key
                        break
            
            # Fallback to nearest neighbor if no BBOX matches (ensures Meknes/Fes/etc. work)
            if not template_key:
                template_key = find_nearest_region(lat, lon)
            
            base_info = MOROCCO_REGIONS.get(template_key, MOROCCO_REGIONS["souss_massa"]).copy()
            
            # Use the provided name or the template name
            display_name = name if name else base_info['name']
            if not display_name.startswith("📍"):
                display_name = f"📍 {display_name}"
            if "Ma Ferme" not in display_name:
                display_name = f"{display_name} (Ma Ferme)"
            
            base_info["name"] = display_name
            base_info["center"] = {"lat": lat, "lon": lon}
            base_info["bbox"] = {"west": lon-0.05, "south": lat-0.05, "east": lon+0.05, "north": lat+0.05}
            
            CUSTOM_REGIONS[region_key] = base_info
            MOROCCO_REGIONS[region_key] = base_info
            
        return region_key
    return region


# ── Climate profiles for realistic per-region data ─────
CLIMATE_PROFILES = {
    "Aride": {"temp_base": 32, "temp_var": 12, "humidity_base": 25, "precip_factor": 0.15, "solar_base": 24, "stress_bias": 0.7},
    "Aride saharien": {"temp_base": 36, "temp_var": 14, "humidity_base": 18, "precip_factor": 0.05, "solar_base": 26, "stress_bias": 0.8},
    "Aride atlantique": {"temp_base": 28, "temp_var": 8, "humidity_base": 55, "precip_factor": 0.1, "solar_base": 22, "stress_bias": 0.5},
    "Aride oceanique": {"temp_base": 24, "temp_var": 6, "humidity_base": 65, "precip_factor": 0.08, "solar_base": 20, "stress_bias": 0.4},
    "Semi-aride": {"temp_base": 28, "temp_var": 12, "humidity_base": 35, "precip_factor": 0.35, "solar_base": 22, "stress_bias": 0.45},
    "Semi-aride continental": {"temp_base": 26, "temp_var": 15, "humidity_base": 32, "precip_factor": 0.3, "solar_base": 21, "stress_bias": 0.5},
    "Semi-aride oceanique": {"temp_base": 22, "temp_var": 8, "humidity_base": 55, "precip_factor": 0.45, "solar_base": 19, "stress_bias": 0.3},
    "Sub-humide": {"temp_base": 20, "temp_var": 10, "humidity_base": 55, "precip_factor": 0.65, "solar_base": 18, "stress_bias": 0.2},
    "Sub-humide oceanique": {"temp_base": 19, "temp_var": 7, "humidity_base": 65, "precip_factor": 0.7, "solar_base": 17, "stress_bias": 0.15},
    "Humide mediterraneen": {"temp_base": 18, "temp_var": 8, "humidity_base": 70, "precip_factor": 0.8, "solar_base": 16, "stress_bias": 0.1},
}


def get_climate_profile(region_key):
    """Get climate profile for a region."""
    if region_key in MOROCCO_REGIONS:
        climate = MOROCCO_REGIONS[region_key].get("climate", "Semi-aride")
    else:
        climate = "Semi-aride"
    return CLIMATE_PROFILES.get(climate, CLIMATE_PROFILES["Semi-aride"])


def region_seed(region_key):
    """Deterministic seed per region for reproducibility."""
    return int(hashlib.md5(region_key.encode()).hexdigest()[:8], 16) % (2**31)


# ── Per-region data generators ─────────────────────────

def generate_region_weather(region_key, days=45):
    """Generate weather data tailored to the region's climate."""
    profile = get_climate_profile(region_key)
    rng = np.random.RandomState(region_seed(region_key))
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    
    # Seasonal patterns
    seasonal = np.cos(2 * np.pi * (day_of_year - 200) / 365)
    
    temp = profile["temp_base"] + profile["temp_var"] * seasonal * 0.5 + rng.normal(0, 2.5, days)
    humidity = np.clip(profile["humidity_base"] - 15 * seasonal + rng.normal(0, 8, days), 10, 95)
    wind = np.clip(3.5 + rng.normal(0, 1.5, days) + seasonal * 0.5, 0.5, 15)
    precip = np.maximum(0, rng.exponential(2, days) * profile["precip_factor"] * (1 + seasonal * 0.3))
    precip[rng.random(days) > 0.3] = 0  # Most days no rain
    solar = np.clip(profile["solar_base"] - 6 * seasonal + rng.normal(0, 2, days), 5, 32)
    
    df = pd.DataFrame({
        "date": dates,
        "temperature": np.round(temp, 1),
        "humidity": np.round(humidity, 1),
        "wind_speed": np.round(wind, 1),
        "precipitation": np.round(precip, 1),
        "solar_radiation": np.round(solar, 1),
    })
    
    # Compute ET0
    fetcher = WeatherFetcher()
    df = fetcher.compute_et0(df)
    return df


def generate_region_patches(region_key, n_patches=20):
    """Generate synthetic patches with stress levels based on region climate."""
    profile = get_climate_profile(region_key)
    rng = np.random.RandomState(region_seed(region_key))
    
    from demo.generate_synthetic import generate_synthetic_patch
    
    images, masks = [], []
    for i in range(n_patches):
        img, msk = generate_synthetic_patch(256, seed=region_seed(region_key) + i)
        
        # Adjust stress based on climate
        bias = profile["stress_bias"]
        # Make arid regions have more stress
        if bias > 0.5:
            # Increase stress levels
            upgrade = rng.random(msk.shape) < (bias - 0.3)
            msk = np.clip(msk + upgrade.astype(int), 0, 3)
        elif bias < 0.3:
            # Decrease stress for humid regions  
            downgrade = rng.random(msk.shape) < (0.5 - bias)
            msk = np.clip(msk - downgrade.astype(int), 0, 3)
        
        images.append(img)
        masks.append(msk)
    
    return np.array(images), np.array(masks)


# ── Per-region cache ───────────────────────────────────
_region_cache = {}
_region_cache_lock = threading.Lock()

def get_region_data(region_key):
    """Get or generate data for a specific region."""
    with _region_cache_lock:
        if region_key in _region_cache:
            return _region_cache[region_key]
        
        print(f"--- Generating fresh data for region: {region_key} ---")
        data = {}
        weather = generate_region_weather(region_key)
        data["weather"] = weather
        data["images"], data["masks"] = generate_region_patches(region_key)
        
        # Generate IoT data
        region_info = MOROCCO_REGIONS.get(region_key)
        if region_info:
            lat, lon = region_info["center"]["lat"], region_info["center"]["lon"]
        else:
            lat, lon = MOROCCO_CENTER["lat"], MOROCCO_CENTER["lon"]
            
        num_sensors = 5 + (region_seed(region_key) % 6)
        simulator = IoTSimulator(num_sensors=num_sensors, center_lat=lat, center_lon=lon)
        readings = simulator.generate_readings(weather)
        
        readings["date_str"] = readings["timestamp"].dt.date.astype(str)
        weather["date_str"] = weather["date"].dt.date.astype(str)
        merged = pd.merge(readings, weather, on="date_str", how="left")
        
        data["iot"] = detect_anomalies(merged)
        
        _region_cache[region_key] = data
        return data


# ── ENDPOINTS ──────────────────────────────────────────

@app.get("/api/regions")
def get_regions():
    """Return all available regions for the dropdown."""
    regions = []
    for key, info in MOROCCO_REGIONS.items():
        regions.append({
            "key": key,
            "name": info["name"],
            "center": info["center"],
            "bbox": info["bbox"],
            "crops": info["crops"],
            "climate": info["climate"],
            "soil": info["soil"],
            "description": info["description"],
        })
    return {"regions": regions}


@app.get("/api/overview")
def get_overview(region: str = Query(None), lat: float = None, lon: float = None, name: str = None):
    # Determine which region key to use
    r_key = ensure_region(region, lat, lon, name)
    
    # Get info: priority to our custom registry, then global ones
    region_info = CUSTOM_REGIONS.get(r_key)
    if not region_info:
        region_info = MOROCCO_REGIONS.get(r_key, MOROCCO_REGIONS["souss_massa"])
    
    # Final safety check for Marrakech name in case of any lookup issues
    if lat is not None and (31.0 <= lat <= 32.5) and lon is not None and (-9.5 <= lon <= -6.5):
        if "Marrakech" not in region_info["name"]:
            region_info = MOROCCO_REGIONS["marrakech_safi"].copy()
            region_info["name"] = f"📍 {region_info['name']} (Ma Ferme)"

    data = get_region_data(r_key)
    weather = data.get("weather")
    images = data.get("images", np.array([]))
    masks = data.get("masks", np.array([]))
    
    n_patches = len(images)
    avg_et0 = float(weather["et0"].mean()) if weather is not None else 0
    last_et0 = float(weather["et0"].tail(7).mean()) if weather is not None else 0
    
    # Stress distribution across all patches
    if len(masks) > 0:
        all_pixels = masks.flatten()
        total = all_pixels.size
        stress_dist = {}
        for lvl in range(4):
            count = int(np.sum(all_pixels == lvl))
            stress_dist[STRESS_LABELS[lvl]] = {
                "count": count,
                "percentage": round(count / total * 100, 1),
                "color": STRESS_COLORS[lvl],
            }
        stressed_zones = int(np.sum([np.mean(m) > 0.8 for m in masks]))
        severe_zones = int(np.sum([np.sum(m == 3) > m.size * 0.05 for m in masks]))
    else:
        stress_dist = {}
        stressed_zones = 0
        severe_zones = 0
    
    # Water savings computation
    engine = IrrigationDecisionEngine()
    stress_map = masks[0].astype(np.float32) if len(masks) > 0 else np.zeros((256, 256))
    et0_values = weather["et0"].tail(20).values if weather is not None else np.full(20, 4.0)
    rng = np.random.RandomState(region_seed(region))
    moisture_map = rng.uniform(15, 65, stress_map.shape)
    recommendations = engine.analyze_zones(stress_map, et0_values, moisture_map, zone_size=32)
    savings = engine.compute_water_savings(recommendations)
    
    # Soil moisture average
    avg_moisture = round(float(moisture_map.mean()), 1)
    
    # Next irrigation time
    schedule = engine.generate_schedule(recommendations)
    next_irrigation = schedule.iloc[0]["start_time"] if len(schedule) > 0 else "Aucune"
    
    return {
        "region": {
            "key": region,
            "name": region_info["name"],
            "climate": region_info["climate"],
            "soil": region_info["soil"],
            "crops": region_info["crops"],
            "description": region_info["description"],
            "center": region_info["center"],
            "bbox": region_info["bbox"],
        },
        "kpis": {
            "water_savings": round(safe_json(savings.get("savings_percent", 0)), 1),
            "patches_analyzed": n_patches,
            "avg_et0": round(avg_et0, 2),
            "last_7d_et0": round(last_et0, 2),
            "forecast_horizon": 48,
            "num_sensors": 5 + (region_seed(region) % 6),
            "stressed_zones": stressed_zones,
            "severe_zones": severe_zones,
            "avg_moisture": avg_moisture,
            "next_irrigation": next_irrigation,
            "total_precision_mm": safe_json(savings.get("total_precision_mm", 0)),
            "total_uniform_mm": safe_json(savings.get("total_uniform_mm", 0)),
            "savings_mm": safe_json(savings.get("savings_mm", 0)),
        },
        "stress_distribution": stress_dist,
        "center": region_info["center"],
        "bbox": region_info["bbox"],
    }


@app.get("/api/alerts")
def get_alerts(region: str = Query(None), lat: float = None, lon: float = None, name: str = None):
    """Generate contextual alerts for a region."""
    r_key = ensure_region(region, lat, lon, name)
    data = get_region_data(r_key)
    weather = data.get("weather")
    masks = data.get("masks", np.array([]))
    region_info = MOROCCO_REGIONS.get(r_key, MOROCCO_REGIONS["souss_massa"])
    profile = get_climate_profile(r_key)
    
    alerts = []
    
    # Stress alerts
    if len(masks) > 0:
        severe_count = sum(1 for m in masks if np.sum(m == 3) > m.size * 0.03)
        moderate_count = sum(1 for m in masks if np.mean(m) > 0.6)
        
        if severe_count > 0:
            alerts.append({
                "type": "danger",
                "icon": "🚨",
                "title": f"{severe_count} zone(s) en stress sévère",
                "message": f"Intervention immédiate recommandée. Risque de perte de rendement.",
                "action": "Voir Plan d'Irrigation",
                "page": "recommendations",
            })
        if moderate_count > 2:
            alerts.append({
                "type": "warning",
                "icon": "⚠️",
                "title": f"{moderate_count} zones sous surveillance",
                "message": "Stress modéré détecté — augmentation possible dans les prochaines 48h.",
                "action": "Voir Analyse",
                "page": "stress",
            })
    
    # Weather alerts
    if weather is not None:
        last_3 = weather.tail(3)
        if last_3["precipitation"].sum() > 0:
            alerts.append({
                "type": "info",
                "icon": "🌧️",
                "title": "Précipitations récentes détectées",
                "message": f"{round(float(last_3['precipitation'].sum()), 1)} mm tombés ces 3 derniers jours. Réduction d'irrigation possible.",
                "action": "Voir Météo",
                "page": "forecast",
            })
        
        last_7_et0 = weather.tail(7)["et0"].mean()
        yearly_et0 = weather["et0"].mean()
        if last_7_et0 > yearly_et0 * 1.2:
            alerts.append({
                "type": "warning",
                "icon": "🌡️",
                "title": "Évapotranspiration élevée",
                "message": f"ET0 moyenne sur 7j: {round(float(last_7_et0), 1)} mm/j — supérieure à la normale ({round(float(yearly_et0), 1)} mm/j).",
                "action": "Voir Prévisions",
                "page": "forecast",
            })
    
    # General irrigation alert
    alerts.append({
        "type": "success",
        "icon": "💧",
        "title": "Prochaine irrigation recommandée",
        "message": f"Demain à 05:00 — irrigation ciblée pour les zones prioritaires.",
        "action": "Voir Planning",
        "page": "recommendations",
    })
    
    # Climate-specific alerts
    if profile["stress_bias"] > 0.6:
        alerts.append({
            "type": "warning",
            "icon": "☀️",
            "title": f"Climat {region_info['climate']} — Vigilance sécheresse",
            "message": "Les conditions climatiques de cette région nécessitent une surveillance accrue de l'humidité du sol.",
            "action": "Voir Carte",
            "page": "map",
        })
    
    return {"alerts": alerts}


@app.get("/api/weather")
def get_weather(region: str = Query(None), days: int = Query(90), lat: float = None, lon: float = None):
    """Return historical and forecasted weather."""
    r_key = ensure_region(region, lat, lon)
    data = get_region_data(r_key)
    weather = data.get("weather")
    if weather is None:
        return {"data": []}
    
    df = weather.tail(days).copy()
    df["date"] = df["date"].astype(str)
    return {"data": df_to_records(df)}


@app.get("/api/weather/stats")
def get_weather_stats(region: str = Query(None), lat: float = None, lon: float = None):
    """Return weather statistics (current vs average)."""
    r_key = ensure_region(region, lat, lon)
    data = get_region_data(r_key)
    weather = data.get("weather")
    if weather is None:
        return {}
    
    last_30 = weather.tail(30)
    full = weather
    
    return {
        "current": {
            "temp_avg": round(float(last_30["temperature"].mean()), 1),
            "temp_delta": round(float(last_30["temperature"].mean() - full["temperature"].mean()), 1),
            "humidity_avg": round(float(last_30["humidity"].mean()), 0),
            "precip_total": round(float(last_30["precipitation"].sum()), 0),
            "solar_avg": round(float(last_30["solar_radiation"].mean()), 1),
            "et0_avg": round(float(last_30["et0"].mean()), 2),
            "et0_delta": round(float(last_30["et0"].mean() - full["et0"].mean()), 2),
        }
    }


@app.get("/api/patches/{patch_id}")
def get_patch_details(patch_id: int, region: str = Query(None), lat: float = None, lon: float = None):
    """Return details for a specific field patch."""
    r_key = ensure_region(region, lat, lon)
    data = get_region_data(r_key)
    images = data.get("images", np.array([]))
    masks = data.get("masks", np.array([]))
    
    if patch_id >= len(images):
        return {"error": "Patch not found"}
    
    image = images[patch_id]
    mask = masks[patch_id]
    
    # Downsample for JSON transfer (64x64 preview)
    step = max(1, image.shape[1] // 64)
    ndvi_small = image[0, ::step, ::step].tolist()
    ndmi_small = image[1, ::step, ::step].tolist()
    mask_small = mask[::step, ::step].tolist()
    
    # Stats
    total = mask.size
    stats = {}
    for lvl in range(4):
        count = int(np.sum(mask == lvl))
        stats[STRESS_LABELS[lvl]] = {
            "count": count,
            "percentage": round(count / total * 100, 1),
            "color": STRESS_COLORS[lvl],
        }
    
    stress_score = round(float(mask.mean() / 3.0), 3)
    
    return {
        "patch_id": patch_id,
        "total_patches": len(images),
        "ndvi": ndvi_small,
        "ndmi": ndmi_small,
        "mask": mask_small,
        "stats": stats,
        "stress_score": stress_score,
        "ndvi_range": [round(float(image[0].min()), 3), round(float(image[0].max()), 3)],
        "ndmi_range": [round(float(image[1].min()), 3), round(float(image[1].max()), 3)],
    }


@app.get("/api/recommendations")
def get_recommendations(region: str = Query(None), lat: float = None, lon: float = None):
    """Return strategic recommendations for the region."""
    r_key = ensure_region(region, lat, lon)
    data = get_region_data(r_key)
    masks = data.get("masks", np.array([]))
    weather = data.get("weather")
    
    if len(masks) == 0:
        return {"recommendations": [], "savings": {}, "schedule": []}
    
    engine = IrrigationDecisionEngine()
    stress_map = masks[0].astype(np.float32)
    et0_values = weather["et0"].tail(20).values if weather is not None else np.full(20, 4.0)
    
    rng = np.random.RandomState(region_seed(r_key))
    moisture_map = rng.uniform(15, 65, stress_map.shape)
    
    recommendations = engine.analyze_zones(stress_map, et0_values, moisture_map, zone_size=32)
    savings = engine.compute_water_savings(recommendations)
    schedule = engine.generate_schedule(recommendations)
    
    # Convert types
    savings_clean = {k: safe_json(v) for k, v in savings.items()}
    if "zones_by_priority" in savings_clean and isinstance(savings_clean["zones_by_priority"], dict):
        savings_clean["zones_by_priority"] = {
            k: safe_json(v) for k, v in savings_clean["zones_by_priority"].items()
        }
    
    return {
        "recommendations": df_to_records(recommendations),
        "savings": savings_clean,
        "schedule": df_to_records(schedule),
    }


@app.get("/api/map/zones")
def get_map_zones(region: str = Query(None), lat: float = None, lon: float = None):
    """Return GeoJSON features for map zones."""
    r_key = ensure_region(region, lat, lon)
    region_info = MOROCCO_REGIONS.get(r_key, MOROCCO_REGIONS["souss_massa"])
    center = region_info["center"]
    bbox = region_info["bbox"]
    profile = get_climate_profile(r_key)
    
    rng = np.random.RandomState(region_seed(r_key))
    zones = []
    stress_colors_map = {0: "#2E7D32", 1: "#F9A825", 2: "#EF6C00", 3: "#C62828"}
    
    # More stressed zones in arid regions
    if profile["stress_bias"] > 0.5:
        weights = [2, 2, 3, 3]
    elif profile["stress_bias"] > 0.3:
        weights = [4, 3, 2, 1]
    else:
        weights = [6, 3, 1, 0]
    
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    
    num_zones = 12 + rng.randint(0, 8)
    
    for i in range(num_zones):
        stress_level = int(rng.choice([0, 1, 2, 3], p=probs))
        lat_range = bbox["north"] - bbox["south"]
        lon_range = bbox["east"] - bbox["west"]
        zones.append({
            "id": i + 1,
            "lat": round(center["lat"] + rng.uniform(-lat_range * 0.35, lat_range * 0.35), 5),
            "lon": round(center["lon"] + rng.uniform(-lon_range * 0.35, lon_range * 0.35), 5),
            "stress_level": stress_level,
            "stress_label": STRESS_LABELS[stress_level],
            "color": stress_colors_map[stress_level],
            "ndvi": round(float(rng.uniform(0.15 + (1 - profile["stress_bias"]) * 0.2, 0.75)), 2),
            "moisture": round(float(rng.uniform(10 + profile["humidity_base"] * 0.3, 30 + profile["humidity_base"] * 0.5)), 0),
            "crop": rng.choice(region_info["crops"]),
            "needs_irrigation": stress_level >= 2,
        })
    
    return {
        "zones": zones,
        "center": center,
        "bbox": bbox,
        "region_name": region_info["name"],
    }


@app.get("/api/iot")
def get_iot_data(region: str = Query(None), lat: float = None, lon: float = None, name: str = None):
    r_key = ensure_region(region, lat, lon, name)
    data = get_region_data(r_key)
    iot = data.get("iot")
    if iot is None:
        return {"sensors": []}
    
    # Ensure boolean types remain strictly boolean to avoid serialization errors
    latest = iot.sort_values("timestamp").groupby("sensor_id").last().reset_index()
    return {"sensors": df_to_records(latest)}


# ── CROP PLANNER ENDPOINTS ─────────────────────────────

@app.get("/api/crops")
def get_crops(search: str = Query(""), category: str = Query("")):
    """Return the full crop catalog, optionally filtered."""
    crops = get_crop_catalog()
    if search:
        search_lower = search.lower()
        crops = [c for c in crops if search_lower in c["name_en"].lower() or search_lower in c["name_fr"].lower()]
    if category:
        crops = [c for c in crops if c["category"] == category]
    return {"crops": crops, "total": len(crops), "categories": get_categories()}


@app.get("/api/crops/{crop_id}")
def get_crop_detail(crop_id: str):
    """Return detailed info for a single crop."""
    crop = get_crop_by_id(crop_id)
    if crop is None:
        return JSONResponse(status_code=404, content={"error": "Crop not found"})
    return {"crop": crop}


@app.get("/api/planner/climate")
def get_climate_estimate(lat: float = Query(31.6), lon: float = Query(-8.0)):
    """Estimate climate for any world location."""
    climate = estimate_climate(lat, lon)
    return {"climate": climate}


@app.post("/api/planner/estimate")
async def estimate_water_budget(request_data: dict = None):
    """Compute full water budget for one or more crops on a parcel."""
    from fastapi import Request
    import json as _json

    if request_data is None:
        return JSONResponse(status_code=400, content={"error": "Missing request body"})

    lat = request_data.get("lat", 31.6)
    lon = request_data.get("lon", -8.0)
    area_ha = request_data.get("area_ha", 10)
    planting_month = request_data.get("planting_month", 3)
    crops_list = request_data.get("crops", [])

    if len(crops_list) == 0:
        return JSONResponse(status_code=400, content={"error": "No crops selected"})

    result = compute_multi_crop_budget(crops_list, area_ha, lat, lon, planting_month)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
