"""
🌾 Système de Précision Irrigation — Point d'entrée principal.

Modes disponibles :
- demo       : Générer les données synthétiques
- train_unet : Entraîner le modèle U-Net
- train_ts   : Entraîner le modèle de séries temporelles
- predict    : Exécuter le pipeline de prédiction complet
- dashboard  : Lancer le dashboard Streamlit

Usage :
    python run.py --mode demo
    python run.py --mode train_unet --epochs 20 --demo
    python run.py --mode train_ts --model informer --demo
    python run.py --mode predict
    python run.py --mode dashboard
"""
import os
import sys
import argparse

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)


def run_demo():
    """Générer toutes les données de démonstration."""
    from demo.generate_synthetic import generate_all_demo_data
    generate_all_demo_data()


def run_train_unet(args):
    """Entraîner le modèle U-Net."""
    from models.unet.train import train
    
    class TrainArgs:
        model_type = args.model or "unet"
        epochs = args.epochs
        batch_size = args.batch_size
        lr = args.lr
        patience = args.patience
        data_dir = os.path.join(ROOT_DIR, "data", "processed")
        demo = args.demo
    
    train(TrainArgs())


def run_train_ts(args):
    """Entraîner le modèle de séries temporelles."""
    from models.timeseries.train import train
    
    class TrainArgs:
        model_type = args.model or "lstm"
        epochs = args.epochs
        batch_size = args.batch_size
        lr = args.lr
        patience = args.patience
        demo = args.demo
    
    train(TrainArgs())


def run_predict():
    """Exécuter le pipeline de prédiction complet."""
    import numpy as np
    from config.settings import SYNTHETIC_DIR
    from pipeline.indices import classify_stress_combined, compute_stress_statistics
    from pipeline.fusion import IrrigationDecisionEngine
    from pipeline.weather import generate_synthetic_weather, WeatherFetcher
    
    print("=" * 60)
    print("  🌾 Pipeline de Prédiction Complet")
    print("=" * 60)
    
    # 1. Charger ou générer les données satellite
    print("\n📡 Étape 1/4 : Chargement données satellite...")
    synth_path = os.path.join(SYNTHETIC_DIR, "synthetic_dataset.npz")
    if os.path.exists(synth_path):
        npz = np.load(synth_path)
        images = npz["images"]
        masks = npz["masks"]
        print(f"  ✅ {len(images)} patches chargés")
    else:
        print("  ⚠️  Pas de données. Exécutez d'abord: python run.py --mode demo")
        return
    
    # 2. Analyser le stress
    print("\n🔬 Étape 2/4 : Analyse du stress hydrique...")
    sample_ndvi = images[0][0]
    sample_ndmi = images[0][1]
    stress_map = classify_stress_combined(sample_ndvi, sample_ndmi)
    stats = compute_stress_statistics(stress_map)
    
    for label, info in stats.items():
        if isinstance(info, dict):
            print(f"  {label}: {info['percentage']:.1f}%")
    
    # 3. Prévision météo
    print("\n⛅ Étape 3/4 : Prévision météo...")
    weather_df = generate_synthetic_weather(30)
    fetcher = WeatherFetcher()
    weather_df = fetcher.compute_et0(weather_df)
    et0_values = weather_df["et0"].values
    print(f"  ET0 moyen: {et0_values.mean():.2f} mm/jour")
    
    # 4. Fusion et recommandations
    print("\n🧠 Étape 4/4 : Fusion et recommandations...")
    engine = IrrigationDecisionEngine()
    moisture_map = np.random.uniform(20, 60, stress_map.shape)
    
    recommendations = engine.analyze_zones(
        stress_map.astype(np.float32), et0_values, moisture_map, zone_size=32
    )
    savings = engine.compute_water_savings(recommendations)
    schedule = engine.generate_schedule(recommendations)
    
    print(f"\n{'='*60}")
    print(f"  📊 RÉSULTATS")
    print(f"{'='*60}")
    print(f"  Zones analysées    : {savings['n_zones']}")
    print(f"  Irrigation uniforme: {savings['total_uniform_mm']:.0f} mm")
    print(f"  Irrigation précise : {savings['total_precision_mm']:.0f} mm")
    print(f"  💧 Économie d'eau  : {savings['savings_percent']:.1f}%")
    print(f"  Zones sans irrigation : {savings['zones_no_irrigation']}")
    print(f"  Zones urgentes     : {savings['zones_urgent']}")
    
    print(f"\n📋 Planning (5 premières zones) :")
    print(schedule.head().to_string(index=False))
    
    # Sauvegarder les résultats
    results_dir = os.path.join(ROOT_DIR, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    recommendations.to_csv(os.path.join(results_dir, "recommendations.csv"), index=False)
    schedule.to_csv(os.path.join(results_dir, "schedule.csv"), index=False)
    print(f"\n💾 Résultats sauvegardés dans: {results_dir}")
    print("✅ Pipeline terminé!")


def run_dashboard():
    """Lancer le dashboard Streamlit."""
    dashboard_path = os.path.join(ROOT_DIR, "dashboard", "app.py")
    os.system(f"streamlit run \"{dashboard_path}\" --server.headless true")


def main():
    parser = argparse.ArgumentParser(
        description="🌾 Système de Précision Irrigation — Maroc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python run.py --mode demo                         # Générer les données démo
  python run.py --mode train_unet --epochs 20 --demo  # Entraîner U-Net
  python run.py --mode train_ts --model informer --demo # Entraîner Informer
  python run.py --mode predict                      # Pipeline complet
  python run.py --mode dashboard                    # Lancer le dashboard
        """
    )
    
    parser.add_argument(
        "--mode", type=str, required=True,
        choices=["demo", "train_unet", "train_ts", "predict", "dashboard"],
        help="Mode d'exécution"
    )
    parser.add_argument("--model", type=str, default=None,
                       help="Type de modèle (unet/unet_resnet/vit pour vision, lstm/gru/informer pour TS)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--demo", action="store_true", help="Utiliser des données synthétiques")
    
    args = parser.parse_args()
    
    print("")
    print("  ============================================================")
    print("  | Systeme de Precision Irrigation par Vision                |")
    print("  | Satellite et IoT - Maroc 2026                            |")
    print("  ============================================================")
    print("")
    
    if args.mode == "demo":
        run_demo()
    elif args.mode == "train_unet":
        run_train_unet(args)
    elif args.mode == "train_ts":
        run_train_ts(args)
    elif args.mode == "predict":
        run_predict()
    elif args.mode == "dashboard":
        run_dashboard()


if __name__ == "__main__":
    main()
