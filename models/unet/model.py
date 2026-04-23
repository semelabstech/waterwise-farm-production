"""
F3 : Modèle U-Net pour la détection du stress hydrique.

Architecture :
- U-Net avec encodeur ResNet34 (pré-entraîné ImageNet)
- Input : patches 256×256 à 3 canaux (NDVI, NDMI, Red)
- Output : masque de segmentation multi-classes (4 niveaux de stress)

Alternative : Vision Transformer (SegFormer) pour capturer
les relations spatiales à longue distance.
"""
import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Tuple

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import UNET_CONFIG, PATCH_SIZE


# ═══════════════════════════════════════════════════════════
#  Blocs de base U-Net (implémentation native PyTorch)
# ═══════════════════════════════════════════════════════════

class ConvBlock(nn.Module):
    """Double convolution avec BatchNorm et ReLU."""
    
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
    
    def forward(self, x):
        return self.block(x)


class EncoderBlock(nn.Module):
    """Bloc encodeur : ConvBlock + MaxPool."""
    
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = ConvBlock(in_channels, out_channels)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
    
    def forward(self, x):
        skip = self.conv(x)
        pooled = self.pool(skip)
        return pooled, skip


class DecoderBlock(nn.Module):
    """Bloc décodeur : UpConv + Concat + ConvBlock."""
    
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2)
        self.conv = ConvBlock(out_channels * 2, out_channels)
    
    def forward(self, x, skip):
        x = self.up(x)
        # Ajuster la taille si nécessaire
        if x.shape != skip.shape:
            x = nn.functional.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=True)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class AttentionGate(nn.Module):
    """Porte d'attention pour améliorer les skip connections."""
    
    def __init__(self, gate_channels: int, skip_channels: int, inter_channels: int):
        super().__init__()
        self.W_gate = nn.Sequential(
            nn.Conv2d(gate_channels, inter_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(inter_channels),
        )
        self.W_skip = nn.Sequential(
            nn.Conv2d(skip_channels, inter_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(inter_channels),
        )
        self.psi = nn.Sequential(
            nn.Conv2d(inter_channels, 1, kernel_size=1, bias=False),
            nn.BatchNorm2d(1),
            nn.Sigmoid(),
        )
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, gate, skip):
        g = self.W_gate(gate)
        s = self.W_skip(skip)
        # Interpoler g à la taille de s si nécessaire
        if g.shape[2:] != s.shape[2:]:
            g = nn.functional.interpolate(g, size=s.shape[2:], mode='bilinear', align_corners=True)
        psi = self.relu(g + s)
        psi = self.psi(psi)
        return skip * psi


# ═══════════════════════════════════════════════════════════
#  U-Net Complet
# ═══════════════════════════════════════════════════════════

class UNet(nn.Module):
    """
    U-Net pour la segmentation du stress hydrique.
    
    Architecture avec 4 niveaux d'encodeur/décodeur et skip connections.
    Inclut des portes d'attention optionnelles pour une meilleure
    fusion des features multi-échelle.
    
    Args:
        in_channels: Nombre de canaux d'entrée (défaut: 3 — NDVI, NDMI, Red)
        num_classes: Nombre de classes de sortie (défaut: 4 niveaux de stress)
        features: Liste des dimensions des features par niveau
        use_attention: Utiliser les portes d'attention
    """
    
    def __init__(
        self,
        in_channels: int = UNET_CONFIG["in_channels"],
        num_classes: int = UNET_CONFIG["classes"],
        features: list = None,
        use_attention: bool = True,
    ):
        super().__init__()
        if features is None:
            features = [64, 128, 256, 512]
        
        self.use_attention = use_attention
        
        # Encodeur
        self.encoder1 = EncoderBlock(in_channels, features[0])
        self.encoder2 = EncoderBlock(features[0], features[1])
        self.encoder3 = EncoderBlock(features[1], features[2])
        self.encoder4 = EncoderBlock(features[2], features[3])
        
        # Bottleneck
        self.bottleneck = ConvBlock(features[3], features[3] * 2)
        
        # Attention gates
        if use_attention:
            self.attn4 = AttentionGate(features[3] * 2, features[3], features[3] // 2)
            self.attn3 = AttentionGate(features[3], features[2], features[2] // 2)
            self.attn2 = AttentionGate(features[2], features[1], features[1] // 2)
            self.attn1 = AttentionGate(features[1], features[0], features[0] // 2)
        
        # Décodeur
        self.decoder4 = DecoderBlock(features[3] * 2, features[3])
        self.decoder3 = DecoderBlock(features[3], features[2])
        self.decoder2 = DecoderBlock(features[2], features[1])
        self.decoder1 = DecoderBlock(features[1], features[0])
        
        # Couche de classification finale
        self.final = nn.Conv2d(features[0], num_classes, kernel_size=1)
        
        # Dropout
        self.dropout = nn.Dropout2d(p=0.2)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Tensor (B, C, H, W) — patches satellite
            
        Returns:
            Tensor (B, num_classes, H, W) — logits de segmentation
        """
        # Encodeur
        e1, skip1 = self.encoder1(x)
        e2, skip2 = self.encoder2(e1)
        e3, skip3 = self.encoder3(e2)
        e4, skip4 = self.encoder4(e3)
        
        # Bottleneck
        b = self.bottleneck(e4)
        b = self.dropout(b)
        
        # Décodeur avec attention
        if self.use_attention:
            skip4 = self.attn4(b, skip4)
            d4 = self.decoder4(b, skip4)
            skip3 = self.attn3(d4, skip3)
            d3 = self.decoder3(d4, skip3)
            skip2 = self.attn2(d3, skip2)
            d2 = self.decoder2(d3, skip2)
            skip1 = self.attn1(d2, skip1)
            d1 = self.decoder1(d2, skip1)
        else:
            d4 = self.decoder4(b, skip4)
            d3 = self.decoder3(d4, skip3)
            d2 = self.decoder2(d3, skip2)
            d1 = self.decoder1(d2, skip1)
        
        return self.final(d1)
    
    def predict(self, x: torch.Tensor) -> np.ndarray:
        """
        Prédiction avec softmax.
        
        Returns:
            Carte de stress (B, H, W) avec valeurs 0–3
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(probs, dim=1)
        return preds.cpu().numpy()


# ═══════════════════════════════════════════════════════════
#  U-Net avec Encodeur ResNet34 Pré-entraîné
# ═══════════════════════════════════════════════════════════

class UNetResNet(nn.Module):
    """
    U-Net avec encodeur ResNet34 pré-entraîné sur ImageNet.
    
    Utilise segmentation_models_pytorch si disponible,
    sinon utilise l'implémentation native ci-dessus.
    """
    
    def __init__(
        self,
        in_channels: int = UNET_CONFIG["in_channels"],
        num_classes: int = UNET_CONFIG["classes"],
        encoder_name: str = UNET_CONFIG["encoder_name"],
        pretrained: bool = True,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes
        
        try:
            import segmentation_models_pytorch as smp
            self.model = smp.Unet(
                encoder_name=encoder_name,
                encoder_weights="imagenet" if pretrained else None,
                in_channels=in_channels,
                classes=num_classes,
                activation=None,  # On applique softmax dans predict()
            )
            self.backend = "smp"
            print(f"✅ U-Net chargé avec encodeur {encoder_name} (segmentation_models_pytorch)")
        except ImportError:
            print("⚠️  segmentation_models_pytorch non disponible. Utilisation U-Net natif.")
            self.model = UNet(in_channels, num_classes)
            self.backend = "native"
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)
    
    def predict(self, x: torch.Tensor) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            preds = torch.argmax(torch.softmax(logits, dim=1), dim=1)
        return preds.cpu().numpy()


# ═══════════════════════════════════════════════════════════
#  Vision Transformer (SegFormer) — Alternative avancée
# ═══════════════════════════════════════════════════════════

class VisionTransformerSeg(nn.Module):
    """
    Segmentation basée sur Vision Transformer.
    
    Utilise un ViT comme encodeur avec un décodeur MLP
    pour la segmentation sémantique.
    """
    
    def __init__(
        self,
        in_channels: int = UNET_CONFIG["in_channels"],
        num_classes: int = UNET_CONFIG["classes"],
        patch_size: int = 16,
        embed_dim: int = 256,
        depth: int = 6,
        num_heads: int = 8,
        img_size: int = PATCH_SIZE,
    ):
        super().__init__()
        self.patch_size = patch_size
        self.img_size = img_size
        self.num_patches = (img_size // patch_size) ** 2
        
        # Patch embedding
        self.patch_embed = nn.Conv2d(
            in_channels, embed_dim, kernel_size=patch_size, stride=patch_size
        )
        
        # Position embedding
        self.pos_embed = nn.Parameter(
            torch.randn(1, self.num_patches, embed_dim) * 0.02
        )
        
        # Transformer blocks
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.1,
            activation='gelu',
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=depth)
        
        # Decoder head — remonter à la résolution originale
        self.decoder = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Linear(embed_dim * 4, patch_size * patch_size * num_classes),
        )
        
        self.num_classes = num_classes
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        
        # Patch embedding : (B, C, H, W) → (B, N, D)
        patches = self.patch_embed(x)  # (B, D, H/P, W/P)
        patches = patches.flatten(2).transpose(1, 2)  # (B, N, D)
        
        # Ajouter position embedding
        patches = patches + self.pos_embed
        
        # Transformer
        features = self.transformer(patches)  # (B, N, D)
        
        # Décoder chaque patch
        decoded = self.decoder(features)  # (B, N, P*P*C_out)
        
        # Réarranger en image
        P = self.patch_size
        n_h = H // P
        n_w = W // P
        decoded = decoded.view(B, n_h, n_w, P, P, self.num_classes)
        decoded = decoded.permute(0, 5, 1, 3, 2, 4).contiguous()
        decoded = decoded.view(B, self.num_classes, H, W)
        
        return decoded
    
    def predict(self, x: torch.Tensor) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            preds = torch.argmax(torch.softmax(logits, dim=1), dim=1)
        return preds.cpu().numpy()


# ═══════════════════════════════════════════════════════════
#  Fonctions de perte
# ═══════════════════════════════════════════════════════════

class DiceLoss(nn.Module):
    """Dice Loss pour segmentation multi-classes."""
    
    def __init__(self, smooth: float = 1e-6):
        super().__init__()
        self.smooth = smooth
    
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.softmax(logits, dim=1)
        num_classes = logits.shape[1]
        
        # One-hot encode targets
        targets_oh = torch.zeros_like(probs)
        targets_oh.scatter_(1, targets.unsqueeze(1).long(), 1)
        
        # Dice per class
        dims = (0, 2, 3)
        intersection = (probs * targets_oh).sum(dims)
        union = probs.sum(dims) + targets_oh.sum(dims)
        
        dice = (2.0 * intersection + self.smooth) / (union + self.smooth)
        return 1.0 - dice.mean()


class CombinedLoss(nn.Module):
    """Combinaison Dice Loss + Cross-Entropy."""
    
    def __init__(self, dice_weight: float = 0.5, ce_weight: float = 0.5):
        super().__init__()
        self.dice = DiceLoss()
        self.ce = nn.CrossEntropyLoss()
        self.dice_weight = dice_weight
        self.ce_weight = ce_weight
    
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        return (
            self.dice_weight * self.dice(logits, targets)
            + self.ce_weight * self.ce(logits, targets.long())
        )


def get_model(model_type: str = "unet", **kwargs) -> nn.Module:
    """
    Factory pour créer le modèle de segmentation.
    
    Args:
        model_type: "unet", "unet_resnet", ou "vit"
    """
    if model_type == "unet":
        return UNet(**kwargs)
    elif model_type == "unet_resnet":
        return UNetResNet(**kwargs)
    elif model_type == "vit":
        return VisionTransformerSeg(**kwargs)
    else:
        raise ValueError(f"Modèle inconnu: {model_type}")


if __name__ == "__main__":
    print("=== Test Modèles ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Test U-Net natif
    model = UNet(in_channels=3, num_classes=4).to(device)
    x = torch.randn(2, 3, 256, 256).to(device)
    out = model(x)
    print(f"U-Net natif : input={x.shape} → output={out.shape}")
    
    preds = model.predict(x)
    print(f"Prédictions : {preds.shape}, valeurs uniques: {np.unique(preds)}")
    
    # Test ViT
    vit = VisionTransformerSeg(in_channels=3, num_classes=4).to(device)
    out_vit = vit(x)
    print(f"ViT : input={x.shape} → output={out_vit.shape}")
    
    # Test loss
    targets = torch.randint(0, 4, (2, 256, 256)).to(device)
    loss_fn = CombinedLoss()
    loss = loss_fn(out, targets)
    print(f"CombinedLoss: {loss.item():.4f}")
    
    # Compter les paramètres
    n_params_unet = sum(p.numel() for p in model.parameters())
    n_params_vit = sum(p.numel() for p in vit.parameters())
    print(f"\nParamètres U-Net: {n_params_unet:,}")
    print(f"Paramètres ViT : {n_params_vit:,}")
    print("✅ Test modèles réussi")
