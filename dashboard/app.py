"""
🌾 Dashboard Streamlit — Système de Précision Irrigation
Application principale avec navigation multi-pages.
"""
import streamlit as st
import os
import sys
import numpy as np
import pandas as pd

# Path setup
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from config.settings import DASHBOARD_CONFIG, SYNTHETIC_DIR, STRESS_LABELS, STRESS_COLORS

# ─── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title=DASHBOARD_CONFIG["page_title"],
    page_icon=DASHBOARD_CONFIG["page_icon"],
    layout=DASHBOARD_CONFIG["layout"],
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme enhancements */
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #1a2940 50%, #0d2137 100%);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #388E3C 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(27, 94, 32, 0.3);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .main-header h1 {
        color: white !important;
        font-size: 2rem !important;
        margin: 0 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .main-header p {
        color: rgba(255,255,255,0.85) !important;
        margin: 0.5rem 0 0 0 !important;
        font-size: 1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30,50,80,0.9), rgba(20,35,60,0.9));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4CAF50, #81C784);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        color: rgba(255,255,255,0.7);
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1f2e 0%, #162d3d 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h1, 
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #81C784 !important;
    }
    
    /* Cards container */
    .glassmorphism {
        background: rgba(30,50,80,0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(30,50,80,0.5);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1B5E20, #2E7D32) !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 Navigation")
    page = st.radio(
        "Page",
        ["🏠 Accueil", "🗺️ Carte Interactive", "🔬 Analyse du Stress", 
         "📈 Prévisions 48h", "💧 Recommandations"],
        label_visibility="collapsed",
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Paramètres")
    
    model_type = st.selectbox("Modèle Vision", ["U-Net", "U-Net + ResNet34", "Vision Transformer"])
    ts_model = st.selectbox("Modèle Séries", ["LSTM", "GRU", "Informer"])
    
    st.markdown("---")
    st.markdown("### 📍 Zone d'étude")
    lat = st.number_input("Latitude", value=30.5, step=0.1, format="%.2f")
    lon = st.number_input("Longitude", value=-9.0, step=0.1, format="%.2f")
    
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center; color:rgba(255,255,255,0.4); font-size:0.8rem;">'
        '🌱 Precision Irrigation System v1.0<br>Maroc 2026</div>',
        unsafe_allow_html=True,
    )


# ─── Load Demo Data ────────────────────────────────────────
@st.cache_data
def load_demo_data():
    """Charger les données de démonstration."""
    data = {}
    
    # Weather
    weather_path = os.path.join(SYNTHETIC_DIR, "weather_demo.csv")
    if os.path.exists(weather_path):
        data["weather"] = pd.read_csv(weather_path, parse_dates=["date"])
    else:
        # Générer
        from pipeline.weather import generate_synthetic_weather, WeatherFetcher
        df = generate_synthetic_weather(365)
        fetcher = WeatherFetcher()
        data["weather"] = fetcher.compute_et0(df)
    
    # Synthetic patches
    synth_path = os.path.join(SYNTHETIC_DIR, "synthetic_dataset.npz")
    if os.path.exists(synth_path):
        npz = np.load(synth_path)
        data["images"] = npz["images"]
        data["masks"] = npz["masks"]
    else:
        from demo.generate_synthetic import generate_synthetic_patch
        images, masks = [], []
        for i in range(20):
            img, msk = generate_synthetic_patch(256, seed=i)
            images.append(img)
            masks.append(msk)
        data["images"] = np.array(images)
        data["masks"] = np.array(masks)
    
    # IoT
    iot_path = os.path.join(SYNTHETIC_DIR, "iot_summary_demo.csv")
    if os.path.exists(iot_path):
        data["iot"] = pd.read_csv(iot_path)
    
    return data


data = load_demo_data()


# ═══════════════════════════════════════════════════════════
#  PAGE : ACCUEIL
# ═══════════════════════════════════════════════════════════
if page == "🏠 Accueil":
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🌾 Système de Précision Irrigation</h1>
        <p>Intelligence Artificielle pour l'optimisation de l'eau agricole au Maroc</p>
    </div>
    """, unsafe_allow_html=True)
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">~30%</div>
            <div class="metric-label">💧 Économie d'eau visée</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        n_patches = len(data.get("images", []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{n_patches}</div>
            <div class="metric-label">📡 Patches analysés</div>
        </div>""", unsafe_allow_html=True)
    
    with col3:
        if "weather" in data:
            avg_et0 = data["weather"]["et0"].mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_et0:.1f}</div>
                <div class="metric-label">🌡️ ET0 moyen (mm/j)</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">N/A</div>
                <div class="metric-label">🌡️ ET0 moyen</div>
            </div>""", unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">48h</div>
            <div class="metric-label">⏱️ Horizon de prévision</div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Architecture Overview
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown('<div class="glassmorphism">', unsafe_allow_html=True)
        st.markdown("### 📐 Architecture du Système")
        st.markdown("""
        ```
        ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐
        │  Sentinel-2 🛰️  │   │  NASA POWER ☁️ │   │  IoT Sensors 📡│
        │  (Images sat.)  │   │  (Météo API) │   │  (Humidité sol)│
        └────────┬────────┘   └──────┬───────┘   └───────┬────────┘
                 │                    │                    │
                 ▼                    ▼                    ▼
        ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐
        │   NDVI / NDMI   │   │  Prévision   │   │  Lecture temps │
        │   Calcul indices│   │  ET0 à 48h   │   │  réel          │
        └────────┬────────┘   └──────┬───────┘   └───────┬────────┘
                 │                    │                    │
                 ▼                    ▼                    ▼
        ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐
        │   U-Net / ViT   │   │Informer/LSTM │   │  Validation    │
        │   Segmentation  │   │  Time-series │   │  terrain       │
        └────────┬────────┘   └──────┬───────┘   └───────┬────────┘
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                     ▼
                           ┌─────────────────┐
                           │  🧠 FUSION      │
                           │  Score pondéré   │
                           │  → Décision      │
                           └────────┬────────┘
                                    ▼
                           ┌─────────────────┐
                           │  💧 IRRIGATION  │
                           │  Recommandation │
                           │  Où/Quand/Combien│
                           └─────────────────┘
        ```
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div class="glassmorphism">', unsafe_allow_html=True)
        st.markdown("### 🔧 Technologies utilisées")
        
        tech_data = {
            "Composant": ["Vision IA", "Séries temporelles", "Satellite", "Météo", "IoT", "Dashboard"],
            "Technologie": ["U-Net / ViT (PyTorch)", "Informer / LSTM", "Sentinel-2 / Copernicus", "NASA POWER / Open-Meteo", "ESP32 / MQTT", "Streamlit / Folium"],
            "Rôle": ["Segmentation stress", "Prévision ET0 48h", "Images multispectrales", "Température, pluie...", "Humidité du sol", "Visualisation interactive"],
        }
        st.dataframe(pd.DataFrame(tech_data), use_container_width=True, hide_index=True)
        
        st.markdown("### 📊 Sources de données")
        st.info("🛰️ **Sentinel-2 L2A** — Images satellite gratuites (ESA/Copernicus)")
        st.success("⛅ **NASA POWER / Open-Meteo** — Données météo historiques et prévisions")
        st.warning("📡 **Capteurs IoT** — Humidité du sol en temps réel")
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  PAGE : CARTE INTERACTIVE  
# ═══════════════════════════════════════════════════════════
elif page == "🗺️ Carte Interactive":
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ Carte Interactive</h1>
        <p>Visualisation des zones agricoles et du stress hydrique</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        import folium
        from streamlit_folium import st_folium
        
        # Créer la carte
        m = folium.Map(
            location=[lat, lon],
            zoom_start=10,
            tiles="OpenStreetMap",
        )
        
        # Ajouter différents fonds de carte
        folium.TileLayer('Esri.WorldImagery', name='Satellite', attr='Esri').add_to(m)
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
        
        # Simuler des zones de stress sur la carte
        np.random.seed(42)
        stress_colors_map = {0: "green", 1: "orange", 2: "red", 3: "darkred"}
        stress_labels_map = {0: "Normal", 1: "Stress Léger", 2: "Stress Modéré", 3: "Stress Sévère"}
        
        for i in range(15):
            zone_lat = lat + np.random.uniform(-0.3, 0.3)
            zone_lon = lon + np.random.uniform(-0.3, 0.3)
            stress_level = np.random.choice([0, 0, 0, 1, 1, 2, 3])
            moisture = np.random.uniform(15, 70)
            
            popup_html = f"""
            <div style="font-family:Arial; min-width:200px;">
                <h4 style="color:#1B5E20; margin-bottom:5px;">Zone {i+1}</h4>
                <table style="width:100%;">
                    <tr><td><b>Stress:</b></td><td>{stress_labels_map[stress_level]}</td></tr>
                    <tr><td><b>NDVI:</b></td><td>{np.random.uniform(0.2, 0.7):.2f}</td></tr>
                    <tr><td><b>Humidité sol:</b></td><td>{moisture:.0f}%</td></tr>
                    <tr><td><b>Irrigation:</b></td><td>{"Oui" if stress_level >= 2 else "Non"}</td></tr>
                </table>
            </div>
            """
            
            folium.CircleMarker(
                location=[zone_lat, zone_lon],
                radius=12 + stress_level * 4,
                color=stress_colors_map[stress_level],
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Zone {i+1}: {stress_labels_map[stress_level]}",
            ).add_to(m)
        
        # Zone d'étude principale (rectangle)
        folium.Rectangle(
            bounds=[[lat - 0.4, lon - 0.4], [lat + 0.4, lon + 0.4]],
            color="#1B5E20",
            weight=2,
            fill=True,
            fill_opacity=0.05,
            tooltip="Zone d'étude principale",
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        st_folium(m, width=None, height=550)
        
        # Légende
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("🟢 **Normal** (NDVI > 0.5)")
        with col2:
            st.markdown("🟠 **Stress Léger** (0.3-0.5)")
        with col3:
            st.markdown("🔴 **Stress Modéré** (0.2-0.3)")
        with col4:
            st.markdown("⭕ **Stress Sévère** (< 0.2)")
            
    except ImportError:
        st.warning("📦 Installez `folium` et `streamlit-folium` pour la carte interactive.")
        st.code("pip install folium streamlit-folium")


# ═══════════════════════════════════════════════════════════
#  PAGE : ANALYSE DU STRESS
# ═══════════════════════════════════════════════════════════
elif page == "🔬 Analyse du Stress":
    st.markdown("""
    <div class="main-header">
        <h1>🔬 Analyse du Stress Hydrique</h1>
        <p>Résultats de segmentation par Deep Learning (U-Net / ViT)</p>
    </div>
    """, unsafe_allow_html=True)
    
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    
    # Sélection du patch
    n_available = min(len(data.get("images", [])), 20)
    if n_available > 0:
        patch_idx = st.slider("Sélectionner un patch satellite", 0, n_available - 1, 0)
        
        image = data["images"][patch_idx]
        mask = data["masks"][patch_idx]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🛰️ NDVI")
            fig, ax = plt.subplots(figsize=(6, 6))
            im = ax.imshow(image[0], cmap='RdYlGn', vmin=-0.2, vmax=0.8)
            ax.axis('off')
            plt.colorbar(im, ax=ax, fraction=0.046)
            fig.patch.set_alpha(0)
            st.pyplot(fig)
            plt.close()
        
        with col2:
            st.markdown("#### 💧 NDMI")
            fig, ax = plt.subplots(figsize=(6, 6))
            im = ax.imshow(image[1], cmap='RdYlBu', vmin=-0.3, vmax=0.5)
            ax.axis('off')
            plt.colorbar(im, ax=ax, fraction=0.046)
            fig.patch.set_alpha(0)
            st.pyplot(fig)
            plt.close()
        
        with col3:
            st.markdown("#### 🎯 Carte de Stress")
            stress_cmap = mcolors.ListedColormap(['#2E7D32', '#F9A825', '#EF6C00', '#C62828'])
            fig, ax = plt.subplots(figsize=(6, 6))
            im = ax.imshow(mask, cmap=stress_cmap, vmin=0, vmax=3)
            ax.axis('off')
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, ticks=[0, 1, 2, 3])
            cbar.set_ticklabels(['Normal', 'Léger', 'Modéré', 'Sévère'])
            fig.patch.set_alpha(0)
            st.pyplot(fig)
            plt.close()
        
        # Statistiques
        st.markdown("---")
        st.markdown("### 📊 Distribution du stress")
        
        col_a, col_b = st.columns([1, 1])
        
        with col_a:
            from pipeline.indices import compute_stress_statistics
            # Simulate stats from mask
            stats_dict = {}
            total = mask.size
            for lvl, lbl in STRESS_LABELS.items():
                cnt = int(np.sum(mask == lvl))
                pct = round(cnt / total * 100, 1)
                stats_dict[lbl] = {"count": cnt, "percentage": pct, "color": STRESS_COLORS[lvl]}
            
            labels = list(stats_dict.keys())
            sizes = [stats_dict[l]["percentage"] for l in labels]
            colors = [stats_dict[l]["color"] for l in labels]
            
            fig, ax = plt.subplots(figsize=(6, 6))
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 11, 'color': 'white'}
            )
            ax.set_title("Répartition du stress", fontsize=14, fontweight='bold', color='white')
            fig.patch.set_alpha(0)
            st.pyplot(fig)
            plt.close()
        
        with col_b:
            st.markdown("#### 📋 Statistiques détaillées")
            stats_df = pd.DataFrame([
                {"Niveau": lbl, "Pixels": stats_dict[lbl]["count"], 
                 "Pourcentage": f"{stats_dict[lbl]['percentage']:.1f}%"}
                for lbl in labels
            ])
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            # Score global
            score = mask.mean() / 3.0
            if score < 0.3:
                st.success(f"🟢 **Score global de stress : {score:.2f}** — Situation normale")
            elif score < 0.5:
                st.warning(f"🟡 **Score global de stress : {score:.2f}** — Surveillance requise")
            else:
                st.error(f"🔴 **Score global de stress : {score:.2f}** — Intervention nécessaire")
    else:
        st.info("🎭 Pas de données. Lancez `python run.py --mode demo` pour générer les données de démo.")


# ═══════════════════════════════════════════════════════════
#  PAGE : PRÉVISIONS 48h
# ═══════════════════════════════════════════════════════════
elif page == "📈 Prévisions 48h":
    st.markdown("""
    <div class="main-header">
        <h1>📈 Prévisions Météo à 48h</h1>
        <p>Modèle Informer / LSTM — Prédiction de l'évapotranspiration (ET0)</p>
    </div>
    """, unsafe_allow_html=True)
    
    if "weather" in data:
        weather = data["weather"]
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Sélection de la période
        n_days_display = st.slider("Jours à afficher", 30, 365, 90)
        df_display = weather.tail(n_days_display)
        
        # Graphique multi-axes avec Plotly
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("🌡️ Température & Humidité", "🌧️ Précipitations", "💧 Évapotranspiration (ET0)"),
        )
        
        # Température
        fig.add_trace(
            go.Scatter(x=df_display["date"], y=df_display["temperature"],
                      name="Température (°C)", line=dict(color="#EF5350", width=2),
                      fill='tozeroy', fillcolor='rgba(239,83,80,0.1)'),
            row=1, col=1
        )
        
        # Humidité
        fig.add_trace(
            go.Scatter(x=df_display["date"], y=df_display["humidity"],
                      name="Humidité (%)", line=dict(color="#42A5F5", width=2),
                      yaxis="y2"),
            row=1, col=1
        )
        
        # Précipitations
        fig.add_trace(
            go.Bar(x=df_display["date"], y=df_display["precipitation"],
                  name="Pluie (mm)", marker_color='rgba(66,165,245,0.7)'),
            row=2, col=1
        )
        
        # ET0
        fig.add_trace(
            go.Scatter(x=df_display["date"], y=df_display["et0"],
                      name="ET0 (mm/j)", line=dict(color="#66BB6A", width=2.5),
                      fill='tozeroy', fillcolor='rgba(102,187,106,0.15)'),
            row=3, col=1
        )
        
        # ET0 seuil de stress
        fig.add_hline(y=5.0, line_dash="dash", line_color="red", 
                     annotation_text="Seuil stress", row=3, col=1)
        
        fig.update_layout(
            height=700,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(10,22,40,0.8)',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            font=dict(color="white"),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistiques
        st.markdown("---")
        st.markdown("### 📊 Résumé statistique")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        last_30 = weather.tail(30)
        
        col1.metric("🌡️ Temp. moy.", f"{last_30['temperature'].mean():.1f}°C",
                    f"{last_30['temperature'].mean() - weather['temperature'].mean():+.1f}°C")
        col2.metric("💧 Humidité moy.", f"{last_30['humidity'].mean():.0f}%")
        col3.metric("🌧️ Pluie totale", f"{last_30['precipitation'].sum():.0f} mm")
        col4.metric("☀️ Radiation moy.", f"{last_30['solar_radiation'].mean():.1f} MJ/m²")
        col5.metric("💧 ET0 moy.", f"{last_30['et0'].mean():.2f} mm/j",
                    f"{last_30['et0'].mean() - weather['et0'].mean():+.2f}")
    else:
        st.info("⛅ Pas de données météo disponibles.")


# ═══════════════════════════════════════════════════════════
#  PAGE : RECOMMANDATIONS
# ═══════════════════════════════════════════════════════════
elif page == "💧 Recommandations":
    st.markdown("""
    <div class="main-header">
        <h1>💧 Recommandations d'Irrigation</h1>
        <p>Décisions optimisées par fusion satellite + météo + IoT</p>
    </div>
    """, unsafe_allow_html=True)
    
    from pipeline.fusion import IrrigationDecisionEngine
    import plotly.graph_objects as go
    
    engine = IrrigationDecisionEngine()
    
    # Générer des recommandations à partir des données de démo
    if "masks" in data and "weather" in data:
        # Prendre un masque de stress
        stress_map = data["masks"][0].astype(np.float32)
        
        # ET0 des derniers jours
        et0_values = data["weather"]["et0"].tail(20).values
        
        # Humidité du sol simulée
        np.random.seed(42)
        moisture_map = np.random.uniform(15, 65, stress_map.shape)
        
        recommendations = engine.analyze_zones(stress_map, et0_values, moisture_map, zone_size=32)
        savings = engine.compute_water_savings(recommendations)
        schedule = engine.generate_schedule(recommendations)
        
        # KPIs d'économie d'eau
        st.markdown("### 💰 Économies d'eau estimées")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="background: linear-gradient(135deg, #4CAF50, #81C784);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    {savings['savings_percent']:.1f}%</div>
                <div class="metric-label">Économie d'eau</div>
            </div>""", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{savings['total_precision_mm']:.0f}</div>
                <div class="metric-label">Volume précision (mm)</div>
            </div>""", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{savings['total_uniform_mm']:.0f}</div>
                <div class="metric-label">Volume uniforme (mm)</div>
            </div>""", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{savings['savings_mm']:.0f}</div>
                <div class="metric-label">Eau économisée (mm)</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Graphique des recommandations
        tab1, tab2, tab3 = st.tabs(["📊 Volumes par zone", "📋 Planning d'irrigation", "📈 Détails"])
        
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=recommendations["zone_id"],
                y=recommendations["volume_recommended_mm"],
                marker_color=recommendations["color"],
                text=recommendations["priority"],
                textposition="outside",
                name="Volume recommandé",
            ))
            
            fig.add_hline(y=30, line_dash="dash", line_color="white",
                         annotation_text="Irrigation uniforme (30mm)",
                         annotation_font_color="white")
            
            fig.update_layout(
                title="Volume d'irrigation recommandé par zone",
                xaxis_title="Zone",
                yaxis_title="Volume (mm)",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(10,22,40,0.8)',
                height=450,
                font=dict(color="white"),
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if len(schedule) > 0:
                st.dataframe(
                    schedule.style.applymap(
                        lambda x: 'background-color: #C62828' if x == 'Urgente' 
                        else ('background-color: #EF6C00' if x == 'Haute'
                        else ('background-color: #F9A825; color: black' if x == 'Moyenne'
                        else '')),
                        subset=['priority']
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.info(f"⏰ Irrigation planifiée entre **05:00 et 08:00** (heures fraîches)")
            else:
                st.success("✅ Aucune irrigation nécessaire aujourd'hui!")
        
        with tab3:
            st.dataframe(
                recommendations[["zone_id", "stress_mean", "stress_label", "et0_predicted",
                                "soil_moisture", "score", "priority", "volume_recommended_mm"]],
                use_container_width=True,
                hide_index=True,
            )
        
        # Export
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv = recommendations.to_csv(index=False)
            st.download_button(
                "📥 Exporter les recommandations (CSV)",
                csv, "recommandations_irrigation.csv", "text/csv",
                use_container_width=True,
            )
        with col_exp2:
            if len(schedule) > 0:
                csv_schedule = schedule.to_csv(index=False)
                st.download_button(
                    "📥 Exporter le planning (CSV)",
                    csv_schedule, "planning_irrigation.csv", "text/csv",
                    use_container_width=True,
                )
    else:
        st.info("🎭 Lancez le mode démo pour générer les recommandations.")
