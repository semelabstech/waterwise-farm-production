"""
Script d'entraînement du modèle U-Net pour la segmentation du stress hydrique.

Features :
- Entraînement avec Dice Loss + Cross-Entropy
- Mixed precision (FP16) pour GPU
- Early stopping
- Sauvegarde des meilleurs checkpoints
- Métriques : IoU, F1, Dice Coefficient
- Support mode démo (données synthétiques)
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
from torch.cuda.amp import GradScaler, autocast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import UNET_CONFIG, CHECKPOINT_DIR, SYNTHETIC_DIR
from models.unet.model import UNet, UNetResNet, VisionTransformerSeg, CombinedLoss, get_model
from models.unet.dataset import create_dataloaders, SatelliteDataset


def compute_iou(preds: torch.Tensor, targets: torch.Tensor, num_classes: int = 4) -> dict:
    """Calculer IoU (Intersection over Union) par classe."""
    ious = {}
    for c in range(num_classes):
        pred_c = (preds == c)
        target_c = (targets == c)
        intersection = (pred_c & target_c).sum().float()
        union = (pred_c | target_c).sum().float()
        iou = (intersection / (union + 1e-6)).item()
        ious[f"class_{c}"] = round(iou, 4)
    
    ious["mean"] = round(np.mean(list(ious.values())), 4)
    return ious


def compute_f1(preds: torch.Tensor, targets: torch.Tensor, num_classes: int = 4) -> dict:
    """Calculer F1-score par classe."""
    f1s = {}
    for c in range(num_classes):
        pred_c = (preds == c)
        target_c = (targets == c)
        tp = (pred_c & target_c).sum().float()
        fp = (pred_c & ~target_c).sum().float()
        fn = (~pred_c & target_c).sum().float()
        precision = tp / (tp + fp + 1e-6)
        recall = tp / (tp + fn + 1e-6)
        f1 = 2 * precision * recall / (precision + recall + 1e-6)
        f1s[f"class_{c}"] = round(f1.item(), 4)
    
    f1s["mean"] = round(np.mean(list(f1s.values())), 4)
    return f1s


def train_epoch(model, loader, optimizer, loss_fn, device, scaler=None):
    """Entraîner le modèle pour une époque."""
    model.train()
    total_loss = 0
    n_batches = 0
    
    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)
        
        optimizer.zero_grad()
        
        if scaler is not None:
            with autocast():
                outputs = model(images)
                loss = loss_fn(outputs, masks)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = loss_fn(outputs, masks)
            loss.backward()
            optimizer.step()
        
        total_loss += loss.item()
        n_batches += 1
    
    return total_loss / max(n_batches, 1)


@torch.no_grad()
def validate(model, loader, loss_fn, device, num_classes=4):
    """Évaluer le modèle sur le set de validation."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    n_batches = 0
    
    for images, masks in loader:
        images = images.to(device)
        masks = masks.to(device)
        
        outputs = model(images)
        loss = loss_fn(outputs, masks)
        
        preds = torch.argmax(outputs, dim=1)
        all_preds.append(preds.cpu())
        all_targets.append(masks.cpu())
        
        total_loss += loss.item()
        n_batches += 1
    
    avg_loss = total_loss / max(n_batches, 1)
    
    all_preds = torch.cat(all_preds)
    all_targets = torch.cat(all_targets)
    
    ious = compute_iou(all_preds, all_targets, num_classes)
    f1s = compute_f1(all_preds, all_targets, num_classes)
    
    return avg_loss, ious, f1s


def train(args):
    """Pipeline d'entraînement complet."""
    print("=" * 60)
    print("  🌾 Entraînement U-Net — Stress Hydrique")
    print("=" * 60)
    
    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"📱 Device: {device}")
    
    # Générer des données synthétiques si mode démo
    if args.demo:
        print("🎭 Mode démo — génération de données synthétiques...")
        from demo.generate_synthetic import generate_synthetic_dataset
        generate_synthetic_dataset(n_samples=200, output_dir=SYNTHETIC_DIR)
        data_dir = SYNTHETIC_DIR
    else:
        data_dir = args.data_dir
    
    # DataLoaders
    train_loader, val_loader, test_loader = create_dataloaders(
        data_dir=data_dir,
        batch_size=args.batch_size,
    )
    
    # Modèle
    model = get_model(
        args.model_type,
        in_channels=UNET_CONFIG["in_channels"],
        num_classes=UNET_CONFIG["classes"],
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 Modèle: {args.model_type} ({n_params:,} paramètres)")
    
    # Loss, Optimizer, Scheduler
    loss_fn = CombinedLoss(dice_weight=0.5, ce_weight=0.5)
    optimizer = AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=UNET_CONFIG["weight_decay"]
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    
    # Mixed precision
    scaler = GradScaler() if device.type == "cuda" else None
    
    # Training loop
    best_iou = 0
    patience_counter = 0
    history = {"train_loss": [], "val_loss": [], "val_iou": [], "val_f1": []}
    
    print(f"\n{'Epoch':>6} | {'Train Loss':>12} | {'Val Loss':>10} | {'mIoU':>8} | {'mF1':>8} | {'LR':>10}")
    print("-" * 70)
    
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        
        # Train
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, device, scaler)
        
        # Validate
        val_loss, ious, f1s = validate(model, val_loader, loss_fn, device)
        
        # Scheduler step
        scheduler.step()
        
        # Logging
        current_lr = optimizer.param_groups[0]["lr"]
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_iou"].append(ious["mean"])
        history["val_f1"].append(f1s["mean"])
        
        elapsed = time.time() - t0
        print(
            f"{epoch:>6} | {train_loss:>12.4f} | {val_loss:>10.4f} | "
            f"{ious['mean']:>8.4f} | {f1s['mean']:>8.4f} | {current_lr:>10.6f} "
            f"({elapsed:.1f}s)"
        )
        
        # Sauvegarder le meilleur modèle
        if ious["mean"] > best_iou:
            best_iou = ious["mean"]
            patience_counter = 0
            
            os.makedirs(CHECKPOINT_DIR, exist_ok=True)
            checkpoint_path = os.path.join(CHECKPOINT_DIR, f"best_{args.model_type}.pth")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_iou": best_iou,
                "history": history,
            }, checkpoint_path)
            print(f"  💾 Meilleur modèle sauvegardé (mIoU: {best_iou:.4f})")
        else:
            patience_counter += 1
        
        # Early stopping
        if patience_counter >= args.patience:
            print(f"\n⏹️  Early stopping à l'époque {epoch} (patience: {args.patience})")
            break
    
    # Évaluation finale sur le set de test
    print("\n" + "=" * 60)
    print("  📊 Évaluation finale sur le set de test")
    print("=" * 60)
    
    # Charger le meilleur modèle
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"best_{args.model_type}.pth")
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
    
    test_loss, test_ious, test_f1s = validate(model, test_loader, loss_fn, device)
    
    print(f"\nTest Loss: {test_loss:.4f}")
    print(f"Test mIoU: {test_ious['mean']:.4f}")
    print(f"Test mF1:  {test_f1s['mean']:.4f}")
    print("\nIoU par classe:")
    for k, v in test_ious.items():
        if k != "mean":
            print(f"  {k}: {v:.4f}")
    
    print("\n✅ Entraînement terminé!")
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraîner le modèle U-Net")
    parser.add_argument("--model_type", type=str, default="unet", choices=["unet", "unet_resnet", "vit"])
    parser.add_argument("--epochs", type=int, default=UNET_CONFIG["epochs"])
    parser.add_argument("--batch_size", type=int, default=UNET_CONFIG["batch_size"])
    parser.add_argument("--lr", type=float, default=UNET_CONFIG["learning_rate"])
    parser.add_argument("--patience", type=int, default=UNET_CONFIG["patience"])
    parser.add_argument("--data_dir", type=str, default=PROCESSED_DIR)
    parser.add_argument("--demo", action="store_true", help="Utiliser des données synthétiques")
    
    args = parser.parse_args()
    train(args)
