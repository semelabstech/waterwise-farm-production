"""
Configuration globale du Système de Précision Irrigation.
Tous les paramètres sont centralisés ici.
"""
import os

# ─── Chemins ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SATELLITE_DIR = os.path.join(DATA_DIR, "satellite")
WEATHER_DIR = os.path.join(DATA_DIR, "weather")
IOT_DIR = os.path.join(DATA_DIR, "iot")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
SYNTHETIC_DIR = os.path.join(DATA_DIR, "synthetic")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")

# Créer les répertoires s'ils n'existent pas (Silently fail on Vercel Read-Only FS)
for d in [SATELLITE_DIR, WEATHER_DIR, IOT_DIR, PROCESSED_DIR, SYNTHETIC_DIR, CHECKPOINT_DIR]:
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass

# ─── API Endpoints ──────────────────────────────────────────
COPERNICUS_API_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"
COPERNICUS_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

# --- Zone Geographique par defaut (Maroc - plaine du Souss) ---
DEFAULT_BBOX = {
    "west": -9.5,
    "south": 30.0,
    "east": -8.5,
    "north": 31.0,
}
DEFAULT_CENTER = {
    "lat": 30.5,
    "lon": -9.0,
}

# --- Regions Agricoles du Maroc ---
MOROCCO_REGIONS = {
    "souss_massa": {
        "name": "Souss-Massa",
        "center": {"lat": 30.4, "lon": -9.2},
        "bbox": {"west": -9.8, "south": 29.8, "east": -8.4, "north": 31.0},
        "crops": ["Agrumes", "Primeurs", "Arganier"],
        "climate": "Semi-aride",
        "soil": "Alluvial",
        "description": "Premiere region exportatrice de tomates et agrumes du Maroc. Zone de Taroudant et Agadir.",
    },
    "marrakech_safi": {
        "name": "Marrakech-Safi",
        "center": {"lat": 31.6, "lon": -8.0},
        "bbox": {"west": -9.0, "south": 31.0, "east": -7.0, "north": 32.2},
        "crops": ["Olivier", "Cereales", "Agrumes"],
        "climate": "Semi-aride continental",
        "soil": "Argilo-calcaire",
        "description": "Region historique de production d'olives et de cereales. Plaine du Haouz.",
    },
    "fes_meknes": {
        "name": "Fes-Meknes",
        "center": {"lat": 33.9, "lon": -5.0},
        "bbox": {"west": -5.8, "south": 33.3, "east": -4.0, "north": 34.5},
        "crops": ["Cereales", "Olivier", "Vigne"],
        "climate": "Sub-humide",
        "soil": "Vertisol",
        "description": "Plaine de Sais, l'un des greniers a ble du Maroc. Agriculture intensive et irriguee.",
    },
    "rabat_sale_kenitra": {
        "name": "Rabat-Sale-Kenitra",
        "center": {"lat": 34.0, "lon": -6.8},
        "bbox": {"west": -7.2, "south": 33.5, "east": -6.2, "north": 34.6},
        "crops": ["Riz", "Canne a sucre", "Agrumes"],
        "climate": "Sub-humide oceanique",
        "soil": "Alluvial riche",
        "description": "Plaine du Gharb, grande zone rizicole et d'agrumiculture du Maroc.",
    },
    "beni_mellal_khenifra": {
        "name": "Beni Mellal-Khenifra",
        "center": {"lat": 32.3, "lon": -6.4},
        "bbox": {"west": -7.0, "south": 31.8, "east": -5.8, "north": 32.8},
        "crops": ["Olivier", "Betterave", "Cereales"],
        "climate": "Semi-aride",
        "soil": "Calcaire",
        "description": "Plaine du Tadla. Agriculture irriguee avec barrage Bin El Ouidane.",
    },
    "draa_tafilalet": {
        "name": "Draa-Tafilalet",
        "center": {"lat": 31.2, "lon": -5.5},
        "bbox": {"west": -6.5, "south": 30.5, "east": -4.5, "north": 32.0},
        "crops": ["Palmier dattier", "Henne", "Safran"],
        "climate": "Aride",
        "soil": "Sableux oasien",
        "description": "Oasis du Sud-Est. Production de dattes (Majhoul) et de safran de Taliouine.",
    },
    "oriental": {
        "name": "Oriental",
        "center": {"lat": 34.7, "lon": -2.0},
        "bbox": {"west": -3.0, "south": 34.0, "east": -1.5, "north": 35.3},
        "crops": ["Agrumes", "Olivier", "Maraichage"],
        "climate": "Semi-aride continental",
        "soil": "Alluvial",
        "description": "Plaine de la Moulouya et Berkane. Agrumiculture et peche.",
    },
    "tanger_tetouan": {
        "name": "Tanger-Tetouan-Al Hoceima",
        "center": {"lat": 35.2, "lon": -5.5},
        "bbox": {"west": -6.2, "south": 34.8, "east": -4.5, "north": 35.8},
        "crops": ["Cereales", "Fruits rouges", "Cannabis"],
        "climate": "Humide mediterraneen",
        "soil": "Argilo-marneux",
        "description": "Region du Rif. Culture de fruits rouges et agriculture de montagne.",
    },
    "casablanca_settat": {
        "name": "Casablanca-Settat",
        "center": {"lat": 33.2, "lon": -7.5},
        "bbox": {"west": -8.2, "south": 32.6, "east": -6.8, "north": 33.8},
        "crops": ["Cereales", "Betterave", "Maraichage"],
        "climate": "Semi-aride oceanique",
        "soil": "Tirs (vertisol)",
        "description": "Plaine de la Chaouia et Doukkala. Principale zone cerealiere du Maroc.",
    },
    "guelmim_oued_noun": {
        "name": "Guelmim-Oued Noun",
        "center": {"lat": 29.0, "lon": -10.0},
        "bbox": {"west": -10.5, "south": 28.5, "east": -9.2, "north": 29.8},
        "crops": ["Cactus", "Palmier", "Henné"],
        "climate": "Aride saharien",
        "soil": "Sableux",
        "description": "Region saharienne avec agriculture oasienne. Production de cactus et henné.",
    },
    "laayoune_sakia": {
        "name": "Laayoune-Sakia El Hamra",
        "center": {"lat": 27.1, "lon": -13.2},
        "bbox": {"west": -13.8, "south": 26.5, "east": -12.5, "north": 27.8},
        "crops": ["Tomate", "Melon", "Culture sous serre"],
        "climate": "Aride atlantique",
        "soil": "Sableux",
        "description": "Agriculture sous serre dans le Sahara. Production de tomates cerises export.",
    },
    "dakhla_oued_eddahab": {
        "name": "Dakhla-Oued Ed Dahab",
        "center": {"lat": 23.7, "lon": -15.9},
        "bbox": {"west": -16.5, "south": 23.0, "east": -15.0, "north": 24.5},
        "crops": ["Tomate cerise", "Melon", "Culture bio"],
        "climate": "Aride oceanique",
        "soil": "Sableux",
        "description": "Point le plus au sud. Agriculture bio sous serre avec climat frais oceanique unique.",
    },
}

# Maroc complet (vue globale)
MOROCCO_FULL_BBOX = {
    "west": -17.0,
    "south": 21.0,
    "east": -1.0,
    "north": 36.0,
}
MOROCCO_CENTER = {
    "lat": 31.8,
    "lon": -7.1,
}

# ─── Paramètres Satellite ───────────────────────────────────
CLOUD_COVER_THRESHOLD = 20          # % maximum de couverture nuageuse
PATCH_SIZE = 256                     # Taille des patches en pixels
PATCH_OVERLAP = 32                   # Chevauchement des patches
SENTINEL_BANDS = ["B04", "B08", "B11"]  # Red, NIR, SWIR
SENTINEL_RESOLUTION = 10            # Résolution en mètres (B04, B08)

# ─── Seuils de Stress Hydrique ──────────────────────────────
NDVI_THRESHOLDS = {
    "severe": 0.2,      # < 0.2 → stress sévère
    "moderate": 0.3,     # 0.2–0.3 → stress modéré
    "light": 0.5,        # 0.3–0.5 → stress léger
    "normal": 1.0,       # > 0.5 → normal
}

NDMI_THRESHOLDS = {
    "stress": 0.0,       # < 0.0 → déficit hydrique
    "watch": 0.1,        # 0.0–0.1 → à surveiller
    "normal": 1.0,       # > 0.1 → normal
}

STRESS_LABELS = {
    0: "Normal",
    1: "Stress Léger",
    2: "Stress Modéré",
    3: "Stress Sévère",
}

STRESS_COLORS = {
    0: "#2E7D32",   # Vert
    1: "#F9A825",   # Jaune
    2: "#EF6C00",   # Orange
    3: "#C62828",   # Rouge
}

# ─── Paramètres U-Net ──────────────────────────────────────
UNET_CONFIG = {
    "encoder_name": "resnet34",
    "encoder_weights": "imagenet",
    "in_channels": 3,          # NDVI, NDMI, B04
    "classes": 4,              # 0=normal, 1=léger, 2=modéré, 3=sévère
    "learning_rate": 1e-4,
    "batch_size": 8,
    "epochs": 50,
    "patience": 10,            # Early stopping
    "weight_decay": 1e-5,
}

# ─── Paramètres Séries Temporelles ──────────────────────────
TIMESERIES_CONFIG = {
    "input_days": 14,          # Jours d'historique
    "forecast_hours": [24, 48],  # Prévision à 24h et 48h
    "features": ["temperature", "humidity", "wind_speed", "precipitation", "solar_radiation"],
    "hidden_size": 128,
    "num_layers": 2,
    "dropout": 0.2,
    "learning_rate": 1e-3,
    "batch_size": 32,
    "epochs": 100,
    "patience": 15,
}

# ─── Paramètres Informer ────────────────────────────────────
INFORMER_CONFIG = {
    "d_model": 64,
    "n_heads": 4,
    "e_layers": 2,            # Encoder layers
    "d_layers": 1,            # Decoder layers
    "d_ff": 256,              # Feedforward dimension
    "factor": 3,              # ProbSparse attention factor
    "dropout": 0.1,
    "activation": "gelu",
}

# ─── Paramètres Fusion ──────────────────────────────────────
FUSION_WEIGHTS = {
    "satellite_stress": 0.40,
    "weather_prediction": 0.35,
    "iot_humidity": 0.25,
}

IRRIGATION_THRESHOLDS = {
    "none": 0.3,     # Score < 0.3 → pas d'irrigation
    "light": 0.5,    # 0.3–0.5 → irrigation légère (5–10 mm)
    "standard": 0.7, # 0.5–0.7 → irrigation standard (15–25 mm)
    "intensive": 1.0, # > 0.7 → irrigation intensive (30–50 mm)
}

IRRIGATION_VOLUMES = {
    "none": (0, 0),
    "light": (5, 10),
    "standard": (15, 25),
    "intensive": (30, 50),
}

# ─── Paramètres IoT ─────────────────────────────────────────
IOT_CONFIG = {
    "num_sensors": 10,
    "reading_interval_minutes": 30,
    "humidity_range": (5, 95),    # % min, max
    "noise_std": 2.0,             # Bruit gaussien
}

# ─── Dashboard ──────────────────────────────────────────────
DASHBOARD_CONFIG = {
    "page_title": "🌾 WaterWiseFarm - Maroc",
    "page_icon": "🌾",
    "layout": "wide",
    "theme": "dark",
}
