"""
Utilitaires de visualisation.
Graphiques et cartes pour le stress hydrique et les prévisions.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from typing import Optional, Dict
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import STRESS_COLORS, STRESS_LABELS


# Palette de couleurs personnalisée
STRESS_CMAP = mcolors.ListedColormap([
    STRESS_COLORS[0],  # Vert
    STRESS_COLORS[1],  # Jaune
    STRESS_COLORS[2],  # Orange
    STRESS_COLORS[3],  # Rouge
])

NDVI_CMAP = plt.cm.RdYlGn  # Rouge-Jaune-Vert


def plot_ndvi_map(
    ndvi: np.ndarray,
    title: str = "Carte NDVI",
    save_path: Optional[str] = None,
    figsize: tuple = (10, 8),
) -> plt.Figure:
    """Visualiser une carte NDVI."""
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    im = ax.imshow(ndvi, cmap=NDVI_CMAP, vmin=-0.2, vmax=0.8)
    ax.set_title(title, fontsize=16, fontweight='bold', color='#1B5E20')
    ax.axis('off')
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('NDVI', fontsize=12)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_stress_map(
    stress_map: np.ndarray,
    title: str = "Carte de Stress Hydrique",
    save_path: Optional[str] = None,
    figsize: tuple = (10, 8),
) -> plt.Figure:
    """Visualiser la carte de stress hydrique."""
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    im = ax.imshow(stress_map, cmap=STRESS_CMAP, vmin=0, vmax=3)
    ax.set_title(title, fontsize=16, fontweight='bold', color='#1B5E20')
    ax.axis('off')
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, ticks=[0, 1, 2, 3])
    cbar.set_ticklabels([STRESS_LABELS[i] for i in range(4)])
    cbar.set_label('Niveau de Stress', fontsize=12)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_stress_distribution(
    stats: Dict,
    title: str = "Distribution du Stress Hydrique",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Diagramme circulaire de la distribution du stress."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    labels = []
    sizes = []
    colors = []
    
    for level in [0, 1, 2, 3]:
        label = STRESS_LABELS[level]
        if label in stats:
            labels.append(label)
            sizes.append(stats[label]["percentage"])
            colors.append(stats[label]["color"])
    
    # Pie chart
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=90, textprops={'fontsize': 11}
    )
    ax1.set_title("Répartition des zones", fontsize=14, fontweight='bold')
    
    # Bar chart
    ax2.barh(labels, sizes, color=colors, edgecolor='white', height=0.6)
    ax2.set_xlabel("Pourcentage (%)", fontsize=12)
    ax2.set_title("Distribution par niveau", fontsize=14, fontweight='bold')
    ax2.set_xlim(0, 100)
    
    for i, v in enumerate(sizes):
        ax2.text(v + 1, i, f'{v:.1f}%', va='center', fontsize=11)
    
    plt.suptitle(title, fontsize=16, fontweight='bold', color='#1B5E20', y=1.02)
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_weather_timeseries(
    df,
    columns: list = None,
    title: str = "Données Météorologiques",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Tracer les séries temporelles météo."""
    if columns is None:
        columns = ["temperature", "humidity", "precipitation", "et0"]
    
    available = [c for c in columns if c in df.columns]
    n_plots = len(available)
    
    fig, axes = plt.subplots(n_plots, 1, figsize=(14, 3 * n_plots), sharex=True)
    if n_plots == 1:
        axes = [axes]
    
    colors = ['#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA']
    labels = {
        "temperature": ("Température (°C)", "°C"),
        "humidity": ("Humidité (%)", "%"),
        "wind_speed": ("Vent (m/s)", "m/s"),
        "precipitation": ("Précipitations (mm)", "mm"),
        "solar_radiation": ("Radiation (MJ/m²)", "MJ/m²"),
        "et0": ("ET0 (mm/jour)", "mm/j"),
    }
    
    for i, col in enumerate(available):
        ax = axes[i]
        label_info = labels.get(col, (col, ""))
        
        if col == "precipitation":
            ax.bar(df["date"], df[col], color=colors[i], alpha=0.7, width=1)
        else:
            ax.plot(df["date"], df[col], color=colors[i], linewidth=1.5, alpha=0.9)
            ax.fill_between(df["date"], df[col], alpha=0.1, color=colors[i])
        
        ax.set_ylabel(label_info[1], fontsize=11)
        ax.set_title(label_info[0], fontsize=12, fontweight='bold', loc='left')
        ax.grid(True, alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    plt.suptitle(title, fontsize=16, fontweight='bold', color='#1B5E20')
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_training_history(
    history: Dict,
    title: str = "Historique d'entraînement",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Tracer l'historique d'entraînement."""
    n_plots = sum(1 for k in ["train_loss", "val_iou", "val_rmse", "val_r2"] if k in history)
    fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 4))
    if n_plots == 1:
        axes = [axes]
    
    idx = 0
    if "train_loss" in history:
        axes[idx].plot(history["train_loss"], label="Train", color='#1E88E5')
        if "val_loss" in history:
            axes[idx].plot(history["val_loss"], label="Validation", color='#E53935')
        axes[idx].set_title("Loss", fontweight='bold')
        axes[idx].legend()
        axes[idx].grid(True, alpha=0.3)
        idx += 1
    
    if "val_iou" in history:
        axes[idx].plot(history["val_iou"], color='#43A047')
        axes[idx].set_title("mIoU", fontweight='bold')
        axes[idx].grid(True, alpha=0.3)
        idx += 1
    
    if "val_rmse" in history:
        axes[idx].plot(history["val_rmse"], color='#FB8C00')
        axes[idx].set_title("RMSE", fontweight='bold')
        axes[idx].grid(True, alpha=0.3)
        idx += 1
    
    if "val_r2" in history:
        axes[idx].plot(history["val_r2"], color='#8E24AA')
        axes[idx].set_title("R²", fontweight='bold')
        axes[idx].grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_irrigation_recommendations(
    recommendations,
    title: str = "Recommandations d'Irrigation",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Visualiser les recommandations d'irrigation par zone."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Volume par zone
    colors = recommendations["color"].tolist()
    ax1.bar(
        recommendations["zone_id"], 
        recommendations["volume_recommended_mm"],
        color=colors, edgecolor='white'
    )
    ax1.set_xlabel("Zone")
    ax1.set_ylabel("Volume (mm)")
    ax1.set_title("Volume d'irrigation par zone", fontweight='bold')
    ax1.tick_params(axis='x', rotation=45)
    
    # Répartition par priorité
    priority_counts = recommendations["priority"].value_counts()
    priority_colors = {
        "Basse": "#2E7D32",
        "Moyenne": "#F9A825", 
        "Haute": "#EF6C00",
        "Urgente": "#C62828",
    }
    ax2.pie(
        priority_counts.values,
        labels=priority_counts.index,
        colors=[priority_colors.get(p, "#666") for p in priority_counts.index],
        autopct='%1.1f%%',
        startangle=90,
    )
    ax2.set_title("Répartition par priorité", fontweight='bold')
    
    plt.suptitle(title, fontsize=16, fontweight='bold', color='#1B5E20')
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig
