"""
Métriques d'évaluation.

- Segmentation : IoU, Dice/F1, Confusion Matrix
- Régression : MAE, RMSE, R²
"""
import numpy as np
from typing import Dict


# ─── Segmentation Metrics ───────────────────────────────────

def iou_score(preds: np.ndarray, targets: np.ndarray, num_classes: int = 4) -> Dict:
    """Intersection over Union (IoU) par classe."""
    ious = {}
    for c in range(num_classes):
        intersection = np.sum((preds == c) & (targets == c))
        union = np.sum((preds == c) | (targets == c))
        ious[f"class_{c}"] = round(intersection / (union + 1e-6), 4)
    ious["mean"] = round(np.mean([v for v in ious.values()]), 4)
    return ious


def dice_score(preds: np.ndarray, targets: np.ndarray, num_classes: int = 4) -> Dict:
    """Dice coefficient (= F1-score) par classe."""
    dices = {}
    for c in range(num_classes):
        pred_c = (preds == c)
        target_c = (targets == c)
        tp = np.sum(pred_c & target_c)
        fp = np.sum(pred_c & ~target_c)
        fn = np.sum(~pred_c & target_c)
        dice = 2 * tp / (2 * tp + fp + fn + 1e-6)
        dices[f"class_{c}"] = round(dice, 4)
    dices["mean"] = round(np.mean([v for v in dices.values()]), 4)
    return dices


def confusion_matrix(preds: np.ndarray, targets: np.ndarray, num_classes: int = 4) -> np.ndarray:
    """Matrice de confusion."""
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for true_class in range(num_classes):
        for pred_class in range(num_classes):
            cm[true_class, pred_class] = np.sum((targets == true_class) & (preds == pred_class))
    return cm


# ─── Regression Metrics ─────────────────────────────────────

def mae(preds: np.ndarray, targets: np.ndarray) -> float:
    """Mean Absolute Error."""
    return round(float(np.mean(np.abs(preds - targets))), 4)


def rmse(preds: np.ndarray, targets: np.ndarray) -> float:
    """Root Mean Square Error."""
    return round(float(np.sqrt(np.mean((preds - targets) ** 2))), 4)


def r2_score(preds: np.ndarray, targets: np.ndarray) -> float:
    """Coefficient de détermination R²."""
    ss_res = np.sum((targets - preds) ** 2)
    ss_tot = np.sum((targets - targets.mean()) ** 2)
    return round(float(1 - ss_res / (ss_tot + 1e-8)), 4)


def mape(preds: np.ndarray, targets: np.ndarray) -> float:
    """Mean Absolute Percentage Error."""
    mask = targets != 0
    return round(float(np.mean(np.abs((targets[mask] - preds[mask]) / targets[mask])) * 100), 2)


# ─── Summary ────────────────────────────────────────────────

def segmentation_report(preds: np.ndarray, targets: np.ndarray, num_classes: int = 4) -> Dict:
    """Rapport complet de segmentation."""
    return {
        "iou": iou_score(preds, targets, num_classes),
        "dice": dice_score(preds, targets, num_classes),
        "confusion_matrix": confusion_matrix(preds, targets, num_classes).tolist(),
    }


def regression_report(preds: np.ndarray, targets: np.ndarray) -> Dict:
    """Rapport complet de régression."""
    return {
        "mae": mae(preds, targets),
        "rmse": rmse(preds, targets),
        "r2": r2_score(preds, targets),
        "mape": mape(preds, targets),
    }
