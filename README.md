# 🌾 Système de Précision Irrigation par Vision Satellite et IoT

## Thème : Agriculture & Stress Hydrique — Maroc

> Système intelligent utilisant des images satellites Sentinel-2, des capteurs IoT, des modèles de Deep Learning et des prévisions météo pour optimiser l'irrigation et **réduire la consommation d'eau de 30%**.

---

## 📐 Architecture

```
┌─────────────────┐   ┌──────────────┐   ┌────────────────┐
│  Sentinel-2 🛰️   │   │  NASA POWER ☁️│   │  IoT Sensors 📡│
└────────┬────────┘   └──────┬───────┘   └───────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐   ┌──────────────┐   ┌────────────────┐
│  U-Net / ViT    │   │  Informer /  │   │  Humidité sol  │
│  Segmentation   │   │  LSTM        │   │  Temps réel    │
└────────┬────────┘   └──────┬───────┘   └───────┬────────┘
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  🧠 FUSION      │
                    │  → Irrigation   │
                    │  Où/Quand/Combien│
                    └─────────────────┘
```

## 🚀 Installation

```bash
# Installer les dépendances
pip install -r requirements.txt
```

## 📋 Utilisation

### 1. Générer les données de démonstration
```bash
python run.py --mode demo
```

### 2. Entraîner le modèle U-Net (détection stress)
```bash
python run.py --mode train_unet --epochs 20 --demo
```

### 3. Entraîner le modèle de séries temporelles (prévision ET0)
```bash
# LSTM (baseline)
python run.py --mode train_ts --model lstm --demo

# Informer (avancé)
python run.py --mode train_ts --model informer --demo
```

### 4. Exécuter le pipeline complet
```bash
python run.py --mode predict
```

### 5. Lancer le dashboard interactif
```bash
python run.py --mode dashboard
```

## 🧠 Modèles d'IA

| Modèle | Tâche | Architecture | Métriques |
|--------|-------|-------------|-----------|
| **U-Net** | Segmentation stress hydrique | Encodeur ResNet34 + Décodeur avec skip connections + Attention Gates | IoU, F1-Score |
| **ViT** | Segmentation avancée | Vision Transformer avec patch embedding | IoU, F1-Score |
| **LSTM** | Prévision ET0 baseline | 2 couches LSTM bidirectionnelles | RMSE, MAE, R² |
| **Informer** | Prévision ET0 avancée | ProbSparse Self-Attention + Distilling layers | RMSE, MAE, R² |

## 📊 Fonctionnalités

| # | Fonctionnalité | Description |
|---|---------------|-------------|
| F1 | Sélection zone & période | Bounding box, filtrage nuages, téléchargement Sentinel-2 |
| F2 | Préparation satellite | NDVI, NDMI, masquage nuages, patches 256×256 |
| F3 | Détection stress | Segmentation U-Net/ViT : 4 niveaux de stress |
| F4 | Prévision 48h | Informer/LSTM : prédiction ET0 à 24h et 48h |
| F5 | Capteurs IoT | Humidité du sol, validation terrain |
| F6 | Fusion intelligente | Combinaison des 3 sources → recommandation irrigation |

## 🔧 Stack Technique

- **Deep Learning** : PyTorch, segmentation-models-pytorch, timm
- **Satellite** : Copernicus API, rasterio, geopandas
- **Météo** : NASA POWER API, Open-Meteo
- **IoT** : ESP32/Arduino, MQTT, SQLite
- **Dashboard** : Streamlit, Folium, Plotly
- **Évaluation** : torchmetrics, scikit-learn

## 📁 Structure du projet

```
├── config/          # Configuration globale
├── data/            # Données (satellite, météo, IoT)
├── models/
│   ├── unet/        # U-Net + ViT pour segmentation
│   └── timeseries/  # LSTM + Informer pour prévision
├── pipeline/        # Modules de traitement
│   ├── satellite.py # Acquisition Sentinel-2
│   ├── weather.py   # Données météo
│   ├── iot.py       # Capteurs IoT
│   ├── indices.py   # NDVI / NDMI
│   └── fusion.py    # Moteur de décision
├── dashboard/       # Interface Streamlit
├── utils/           # Utilitaires
├── demo/            # Générateur de données démo
├── run.py           # Point d'entrée
└── README.md
```

## 📄 Licence

Projet académique — Maroc 2026
