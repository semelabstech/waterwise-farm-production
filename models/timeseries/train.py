"""
Script d'entraînement des modèles de séries temporelles (LSTM, GRU, Informer).

Prédiction de l'évapotranspiration (ET0) à 24h et 48h.
"""
import os
import sys
import time
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import TIMESERIES_CONFIG, CHECKPOINT_DIR, SYNTHETIC_DIR
from models.timeseries.model import get_timeseries_model
from models.timeseries.dataset import create_timeseries_dataloaders


def train_epoch(model, loader, optimizer, loss_fn, device):
    """Entraîner pour une époque."""
    model.train()
    total_loss = 0
    n_batches = 0
    
    for X, y in loader:
        X, y = X.to(device), y.to(device)
        
        optimizer.zero_grad()
        pred = model(X)
        loss = loss_fn(pred, y)
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1
    
    return total_loss / max(n_batches, 1)


@torch.no_grad()
def validate(model, loader, loss_fn, device, dataset=None):
    """Évaluer le modèle."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    n_batches = 0
    
    for X, y in loader:
        X, y = X.to(device), y.to(device)
        pred = model(X)
        loss = loss_fn(pred, y)
        
        all_preds.append(pred.cpu().numpy())
        all_targets.append(y.cpu().numpy())
        total_loss += loss.item()
        n_batches += 1
    
    avg_loss = total_loss / max(n_batches, 1)
    
    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)
    
    # Dénormaliser si possible
    if dataset is not None:
        try:
            scaler_X, scaler_y = dataset.get_scalers()
            preds_denorm = np.column_stack([
                scaler_y.inverse_transform(preds[:, i:i+1]) for i in range(preds.shape[1])
            ])
            targets_denorm = np.column_stack([
                scaler_y.inverse_transform(targets[:, i:i+1]) for i in range(targets.shape[1])
            ])
        except Exception:
            preds_denorm = preds
            targets_denorm = targets
    else:
        preds_denorm = preds
        targets_denorm = targets
    
    # Métriques
    mae = np.mean(np.abs(preds_denorm - targets_denorm))
    rmse = np.sqrt(np.mean((preds_denorm - targets_denorm) ** 2))
    
    # R²
    ss_res = np.sum((targets_denorm - preds_denorm) ** 2)
    ss_tot = np.sum((targets_denorm - targets_denorm.mean()) ** 2)
    r2 = 1 - (ss_res / (ss_tot + 1e-8))
    
    metrics = {
        "loss": avg_loss,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
    }
    
    return metrics


def train(args):
    """Pipeline d'entraînement complet."""
    print("=" * 60)
    print("  ⛅ Entraînement Séries Temporelles — Prévision ET0")
    print("=" * 60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"📱 Device: {device}")
    
    # Données
    if args.demo:
        print("🎭 Mode démo — données météo synthétiques...")
        from pipeline.weather import generate_synthetic_weather, WeatherFetcher
        weather_df = generate_synthetic_weather(365)
        fetcher = WeatherFetcher()
        weather_df = fetcher.compute_et0(weather_df)
    else:
        weather_df = None
    
    train_loader, val_loader, test_loader, dataset = create_timeseries_dataloaders(
        data=weather_df,
        batch_size=args.batch_size,
    )
    
    # Modèle
    model = get_timeseries_model(args.model_type).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 Modèle: {args.model_type} ({n_params:,} paramètres)")
    
    # Loss, Optimizer, Scheduler
    loss_fn = nn.MSELoss()
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    
    # Training loop
    best_rmse = float("inf")
    patience_counter = 0
    history = {"train_loss": [], "val_loss": [], "val_mae": [], "val_rmse": [], "val_r2": []}
    
    print(f"\n{'Epoch':>6} | {'Train Loss':>12} | {'Val Loss':>10} | {'MAE':>8} | {'RMSE':>8} | {'R²':>8}")
    print("-" * 70)
    
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, device)
        val_metrics = validate(model, val_loader, loss_fn, device, dataset)
        scheduler.step()
        
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_metrics["loss"])
        history["val_mae"].append(val_metrics["mae"])
        history["val_rmse"].append(val_metrics["rmse"])
        history["val_r2"].append(val_metrics["r2"])
        
        elapsed = time.time() - t0
        print(
            f"{epoch:>6} | {train_loss:>12.6f} | {val_metrics['loss']:>10.6f} | "
            f"{val_metrics['mae']:>8.4f} | {val_metrics['rmse']:>8.4f} | "
            f"{val_metrics['r2']:>8.4f} ({elapsed:.1f}s)"
        )
        
        if val_metrics["rmse"] < best_rmse:
            best_rmse = val_metrics["rmse"]
            patience_counter = 0
            
            os.makedirs(CHECKPOINT_DIR, exist_ok=True)
            checkpoint_path = os.path.join(CHECKPOINT_DIR, f"best_ts_{args.model_type}.pth")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "best_rmse": best_rmse,
                "history": history,
                "scaler_X": dataset.scaler_X,
                "scaler_y": dataset.scaler_y,
            }, checkpoint_path)
            print(f"  💾 Meilleur modèle sauvegardé (RMSE: {best_rmse:.4f})")
        else:
            patience_counter += 1
        
        if patience_counter >= args.patience:
            print(f"\n⏹️  Early stopping à l'époque {epoch}")
            break
    
    # Évaluation finale
    print("\n" + "=" * 60)
    print("  📊 Évaluation finale — Set de test")
    print("=" * 60)
    
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"best_ts_{args.model_type}.pth")
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
    
    test_metrics = validate(model, test_loader, loss_fn, device, dataset)
    
    print(f"\nTest MAE:  {test_metrics['mae']:.4f} mm/jour")
    print(f"Test RMSE: {test_metrics['rmse']:.4f} mm/jour")
    print(f"Test R²:   {test_metrics['r2']:.4f}")
    
    print("\n✅ Entraînement terminé!")
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraîner le modèle de séries temporelles")
    parser.add_argument("--model_type", type=str, default="lstm", choices=["lstm", "gru", "informer"])
    parser.add_argument("--epochs", type=int, default=TIMESERIES_CONFIG["epochs"])
    parser.add_argument("--batch_size", type=int, default=TIMESERIES_CONFIG["batch_size"])
    parser.add_argument("--lr", type=float, default=TIMESERIES_CONFIG["learning_rate"])
    parser.add_argument("--patience", type=int, default=TIMESERIES_CONFIG["patience"])
    parser.add_argument("--demo", action="store_true", help="Utiliser des données synthétiques")
    
    args = parser.parse_args()
    train(args)
