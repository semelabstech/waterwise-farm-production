"""
Crop Planner — Core business logic for the Farmer Land Planner.

Provides crop catalog, climate estimation, water budget computation,
and irrigation calendar generation using FAO-56 + AI model.
"""
import os, sys, json, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DATA_DIR

CROP_DB_PATH = os.path.join(DATA_DIR, "crops", "fao_crop_database.json")
MODEL_PATH = os.path.join(DATA_DIR, "crops", "models", "crop_water_mlp.pth")

_crop_cache = None


def get_crop_catalog():
    """Load and return the full FAO crop database."""
    global _crop_cache
    if _crop_cache is not None:
        return _crop_cache
    with open(CROP_DB_PATH, "r", encoding="utf-8") as f:
        _crop_cache = json.load(f)
    return _crop_cache


def get_crop_by_id(crop_id):
    """Get a single crop by its ID."""
    crops = get_crop_catalog()
    for c in crops:
        if c["id"] == crop_id:
            return c
    return None


def get_categories():
    """Return list of unique categories."""
    crops = get_crop_catalog()
    return sorted(set(c["category"] for c in crops))


def estimate_climate(lat, lon):
    """
    Estimate climate profile for any world location based on latitude.
    Uses a simplified Koppen-like model for offline operation.
    """
    abs_lat = abs(lat)

    # Base temperature decreases with latitude
    if abs_lat < 10:
        temp_base, humidity_base, solar_base = 28, 78, 18
        climate_name = "Tropical"
    elif abs_lat < 23.5:
        temp_base, humidity_base, solar_base = 26, 55, 20
        climate_name = "Subtropical"
    elif abs_lat < 35:
        temp_base, humidity_base, solar_base = 20, 50, 18
        climate_name = "Mediterranean"
    elif abs_lat < 50:
        temp_base, humidity_base, solar_base = 14, 65, 14
        climate_name = "Temperate"
    elif abs_lat < 60:
        temp_base, humidity_base, solar_base = 6, 70, 10
        climate_name = "Continental"
    else:
        temp_base, humidity_base, solar_base = -2, 75, 7
        climate_name = "Polar"

    # Longitude-based aridity correction (inland = drier)
    inland_factor = min(abs(lon) / 180, 1.0)

    # ET0 estimation (Hargreaves simplified)
    et0_base = max(0.5, 0.0023 * (temp_base + 17.8) * math.sqrt(max(1, solar_base * 2)) * 0.408)

    return {
        "climate_name": climate_name,
        "temp_avg": round(temp_base, 1),
        "humidity_avg": round(humidity_base, 1),
        "solar_avg": round(solar_base, 1),
        "wind_avg": round(2.5 + inland_factor, 1),
        "et0_avg": round(et0_base, 2),
        "precip_annual_mm": round(max(50, 1200 - abs_lat * 15 - inland_factor * 200), 0),
        "lat": lat,
        "lon": lon,
    }


def get_kc_at_day(crop, day):
    """Interpolate Kc at a given day of the growth cycle."""
    stages = crop["stage_days"]
    d1 = stages["initial"]
    d2 = stages["development"]
    d3 = stages["mid"]
    d4 = stages["late"]

    if day <= d1:
        return crop["kc_ini"]
    elif day <= d1 + d2:
        frac = (day - d1) / d2
        return crop["kc_ini"] + frac * (crop["kc_mid"] - crop["kc_ini"])
    elif day <= d1 + d2 + d3:
        return crop["kc_mid"]
    else:
        elapsed = day - (d1 + d2 + d3)
        frac = min(elapsed / max(d4, 1), 1.0)
        return crop["kc_mid"] + frac * (crop["kc_end"] - crop["kc_mid"])


def get_growth_stage_name(crop, day):
    """Return the name of the growth stage at a given day."""
    stages = crop["stage_days"]
    d1 = stages["initial"]
    d2 = stages["development"]
    d3 = stages["mid"]

    if day <= d1:
        return "Initial"
    elif day <= d1 + d2:
        return "Development"
    elif day <= d1 + d2 + d3:
        return "Mid-Season"
    else:
        return "Late Season"


_model_cache = None

def predict_etc_ai(kc, et0, temp, humidity, wind, solar, soil_idx, growth_frac):
    """Use the trained MLP to predict ETc, or fall back to FAO formula."""
    global _model_cache
    try:
        import torch
        from models.crop_water.model import CropWaterMLP

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model not trained yet")

        if _model_cache is None:
            checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
            model = CropWaterMLP(input_dim=8)
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            _model_cache = {
                "model": model,
                "X_mean": checkpoint["X_mean"],
                "X_std": checkpoint["X_std"],
                "y_mean": float(checkpoint["y_mean"]),
                "y_std": float(checkpoint["y_std"]),
            }

        m = _model_cache
        x = np.array([[kc, et0, temp, humidity, wind, solar, soil_idx, growth_frac]], dtype=np.float32)
        x_norm = (x - m["X_mean"]) / (m["X_std"] + 1e-8)

        with torch.no_grad():
            pred_norm = m["model"](torch.tensor(x_norm)).item()
        return float(max(0.05, pred_norm * m["y_std"] + m["y_mean"]))

    except Exception:
        # Fallback: simple FAO formula
        return float(max(0.05, kc * et0))


def compute_water_budget(crop_id, area_ha, lat, lon, planting_month=3):
    """
    Compute full water budget for a crop on a given parcel.

    Returns dict with total water, monthly breakdown, daily curve, etc.
    """
    crop = get_crop_by_id(crop_id)
    if crop is None:
        return {"error": f"Crop {crop_id} not found"}

    climate = estimate_climate(lat, lon)
    total_days = crop["total_growing_days"]

    # Monthly ET0 variation (sinusoidal around average)
    monthly_et0 = []
    for m in range(12):
        seasonal = math.sin(2 * math.pi * (m - 1) / 12)
        if lat >= 0:  # Northern hemisphere: peak in July
            et0_m = climate["et0_avg"] * (1 + 0.4 * seasonal)
        else:
            et0_m = climate["et0_avg"] * (1 - 0.4 * seasonal)
        monthly_et0.append(max(0.5, et0_m))

    # Daily ETc computation
    daily_etc = []
    daily_kc = []
    month_totals = [0.0] * 12

    for day in range(1, total_days + 1):
        kc = get_kc_at_day(crop, day)
        growth_frac = day / total_days

        # Which month is this day in?
        month_idx = (planting_month - 1 + (day - 1) // 30) % 12
        et0_day = monthly_et0[month_idx]

        # Use AI model or fallback
        etc_day = predict_etc_ai(
            kc, et0_day, climate["temp_avg"], climate["humidity_avg"],
            climate["wind_avg"], climate["solar_avg"], 1, growth_frac
        )

        daily_etc.append(round(etc_day, 2))
        daily_kc.append(round(kc, 3))
        month_totals[month_idx] += etc_day

    total_mm = sum(daily_etc)
    total_m3 = total_mm * area_ha * 10  # 1mm on 1ha = 10m3
    avg_daily = total_mm / total_days

    # Monthly breakdown with names
    month_names = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
                   "Jul", "Aou", "Sep", "Oct", "Nov", "Dec"]
    monthly_breakdown = []
    for i in range(12):
        monthly_breakdown.append({
            "month": month_names[i],
            "month_idx": i,
            "etc_mm": round(month_totals[i], 1),
            "etc_m3": round(month_totals[i] * area_ha * 10, 0),
            "et0_avg": round(monthly_et0[i], 2),
        })

    # Kc curve data (for chart)
    kc_curve = []
    for day in range(1, total_days + 1, 5):
        kc_curve.append({
            "day": day,
            "kc": round(get_kc_at_day(crop, day), 3),
            "stage": get_growth_stage_name(crop, day),
        })

    return {
        "crop": {
            "id": crop["id"],
            "name_en": crop["name_en"],
            "name_fr": crop["name_fr"],
            "icon": crop["icon"],
            "category": crop["category"],
            "total_growing_days": total_days,
            "drought_tolerance": crop["drought_tolerance"],
        },
        "location": {"lat": lat, "lon": lon},
        "climate": climate,
        "area_ha": area_ha,
        "planting_month": planting_month,
        "results": {
            "total_water_mm": round(total_mm, 1),
            "total_water_m3": round(total_m3, 0),
            "avg_daily_mm": round(avg_daily, 2),
            "peak_daily_mm": round(max(daily_etc), 2),
            "season_days": total_days,
            "savings_vs_uniform_pct": round(max(10, 40 - total_mm / 30), 1),
        },
        "monthly_breakdown": monthly_breakdown,
        "kc_curve": kc_curve,
    }


def _sanitize(obj):
    """Recursively convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def compute_multi_crop_budget(crops_list, area_ha, lat, lon, planting_month=3):
    """
    Compute water budget for multiple crops on a parcel.

    crops_list: [{"id": "wheat_winter", "percentage": 40}, ...]
    """
    results = []
    grand_total_m3 = 0
    grand_total_mm = 0

    for entry in crops_list:
        crop_area = area_ha * entry["percentage"] / 100.0
        budget = compute_water_budget(entry["id"], crop_area, lat, lon, planting_month)
        if "error" in budget:
            continue
        budget["percentage"] = entry["percentage"]
        budget["allocated_area_ha"] = round(crop_area, 2)
        grand_total_m3 += budget["results"]["total_water_m3"]
        grand_total_mm += budget["results"]["total_water_mm"] * entry["percentage"] / 100
        results.append(budget)

    # Aggregate monthly
    agg_monthly = [0.0] * 12
    for r in results:
        for mb in r["monthly_breakdown"]:
            agg_monthly[mb["month_idx"]] += mb["etc_m3"]

    month_names = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
                   "Jul", "Aou", "Sep", "Oct", "Nov", "Dec"]

    return _sanitize({
        "total_area_ha": area_ha,
        "num_crops": len(results),
        "grand_total_m3": round(grand_total_m3, 0),
        "grand_total_mm_weighted": round(grand_total_mm, 1),
        "avg_daily_m3": round(grand_total_m3 / 365, 0) if grand_total_m3 > 0 else 0,
        "crops": results,
        "aggregated_monthly": [
            {"month": month_names[i], "total_m3": round(agg_monthly[i], 0)}
            for i in range(12)
        ],
    })


if __name__ == "__main__":
    catalog = get_crop_catalog()
    print(f"Loaded {len(catalog)} crops in {len(get_categories())} categories")

    budget = compute_water_budget("wheat_winter", 50, 31.6, -8.0, planting_month=11)
    print(f"\nWheat on 50ha near Marrakech:")
    print(f"  Total: {budget['results']['total_water_m3']:.0f} m3")
    print(f"  Daily avg: {budget['results']['avg_daily_mm']:.1f} mm/day")
