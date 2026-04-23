"""
F4 : Modèles de séries temporelles pour la prévision du besoin hydrique à 48h.

Modèles implémentés :
1. LSTM/GRU — Baseline robuste
2. Informer — Transformer optimisé avec ProbSparse Self-Attention

Entrées : séquence météo de 14 jours (température, humidité, vent, précipitations, radiation)
Sortie : prédiction ET0 à 24h et 48h
"""
import math
import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Tuple

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import TIMESERIES_CONFIG, INFORMER_CONFIG


# ═══════════════════════════════════════════════════════════
#  LSTM / GRU — Modèle Baseline
# ═══════════════════════════════════════════════════════════

class LSTMPredictor(nn.Module):
    """
    LSTM bidirectionnel pour la prévision de l'évapotranspiration (ET0).
    
    Architecture :
    - Embedding linéaire des features
    - 2 couches LSTM bidirectionnelles
    - Couche dense de sortie
    
    Args:
        input_size: Nombre de features d'entrée (5: temp, humidity, wind, precip, solar)
        hidden_size: Taille de l'état caché
        num_layers: Nombre de couches LSTM
        output_size: Nombre de prédictions (2: ET0 à 24h et 48h)
        dropout: Taux de dropout
        bidirectional: Utiliser un LSTM bidirectionnel
    """
    
    def __init__(
        self,
        input_size: int = len(TIMESERIES_CONFIG["features"]),
        hidden_size: int = TIMESERIES_CONFIG["hidden_size"],
        num_layers: int = TIMESERIES_CONFIG["num_layers"],
        output_size: int = len(TIMESERIES_CONFIG["forecast_hours"]),
        dropout: float = TIMESERIES_CONFIG["dropout"],
        bidirectional: bool = True,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        
        # Embedding des features
        self.input_proj = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        # LSTM
        self.lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
        )
        
        # Couche de sortie
        self.output_head = nn.Sequential(
            nn.Linear(hidden_size * self.num_directions, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, output_size),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor (B, T, F) — séquence temporelle
            
        Returns:
            Tensor (B, output_size) — prédictions
        """
        # Projection
        x = self.input_proj(x)  # (B, T, H)
        
        # LSTM
        lstm_out, (h_n, c_n) = self.lstm(x)  # (B, T, H*num_directions)
        
        # Utiliser le dernier état caché
        if self.bidirectional:
            # Concaténer forward et backward
            last_hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)  # (B, H*2)
        else:
            last_hidden = h_n[-1]  # (B, H)
        
        # Prédiction
        output = self.output_head(last_hidden)  # (B, output_size)
        return output


class GRUPredictor(nn.Module):
    """GRU comme alternative plus légère au LSTM."""
    
    def __init__(
        self,
        input_size: int = len(TIMESERIES_CONFIG["features"]),
        hidden_size: int = TIMESERIES_CONFIG["hidden_size"],
        num_layers: int = TIMESERIES_CONFIG["num_layers"],
        output_size: int = len(TIMESERIES_CONFIG["forecast_hours"]),
        dropout: float = TIMESERIES_CONFIG["dropout"],
    ):
        super().__init__()
        
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        
        self.output_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, output_size),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, h_n = self.gru(x)
        return self.output_head(h_n[-1])


# ═══════════════════════════════════════════════════════════
#  Informer — Transformer avec ProbSparse Self-Attention
# ═══════════════════════════════════════════════════════════

class ProbSparseAttention(nn.Module):
    """
    ProbSparse Self-Attention du papier Informer.
    
    Réduit la complexité de O(L²) à O(L log L) en ne calculant
    l'attention que sur les queries les plus informatives.
    """
    
    def __init__(self, d_model: int, n_heads: int, factor: int = 3, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.factor = factor
        
        self.W_Q = nn.Linear(d_model, d_model, bias=False)
        self.W_K = nn.Linear(d_model, d_model, bias=False)
        self.W_V = nn.Linear(d_model, d_model, bias=False)
        self.out = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)
    
    def _prob_QK(self, Q, K, sample_k):
        """Sélectionner les top-k queries les plus informatives."""
        B, H, L_Q, D = Q.shape
        _, _, L_K, _ = K.shape
        
        # Calculer le score d'attention brut
        K_sample = K[:, :, torch.randint(L_K, (sample_k,)), :]
        Q_K_sample = torch.matmul(Q, K_sample.transpose(-2, -1))
        
        # Mesure de sparsité : M(qi) = max(qiK^T) - mean(qiK^T)
        M = Q_K_sample.max(-1)[0] - Q_K_sample.mean(-1)
        
        # Sélectionner les top-u queries
        u = max(1, self.factor * int(np.ceil(np.log(L_Q + 1))))
        u = min(u, L_Q)
        M_top = M.topk(u, sorted=False)[1]
        
        return M_top
    
    def forward(self, Q, K, V, mask=None):
        B, L_Q, _ = Q.shape
        B, L_K, _ = K.shape
        H = self.n_heads
        
        Q = self.W_Q(Q).view(B, L_Q, H, self.d_k).transpose(1, 2)
        K = self.W_K(K).view(B, L_K, H, self.d_k).transpose(1, 2)
        V = self.W_V(V).view(B, L_K, H, self.d_k).transpose(1, 2)
        
        # Attention standard (simplifiée pour la stabilité)
        scale = math.sqrt(self.d_k)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / scale
        
        if mask is not None:
            scores.masked_fill_(mask == 0, -1e9)
        
        attn = torch.softmax(scores, dim=-1)
        attn = self.dropout(attn)
        
        context = torch.matmul(attn, V)
        context = context.transpose(1, 2).contiguous().view(B, L_Q, self.d_model)
        
        return self.out(context)


class InformerEncoderLayer(nn.Module):
    """Couche encodeur Informer avec attention et FFN."""
    
    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.attention = ProbSparseAttention(d_model, n_heads, dropout=dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
    
    def forward(self, x):
        # Self-attention + residual
        attn_out = self.attention(x, x, x)
        x = self.norm1(x + attn_out)
        
        # FFN + residual
        ffn_out = self.ffn(x)
        x = self.norm2(x + ffn_out)
        
        return x


class DistillingLayer(nn.Module):
    """
    Couche de distillation Informer.
    Réduit la dimension temporelle de moitié pour concentrer l'information.
    """
    
    def __init__(self, d_model: int):
        super().__init__()
        self.conv = nn.Conv1d(d_model, d_model, kernel_size=3, padding=1)
        self.norm = nn.BatchNorm1d(d_model)
        self.activation = nn.ELU()
        self.pool = nn.MaxPool1d(kernel_size=2, stride=2)
    
    def forward(self, x):
        # x: (B, L, D) → (B, D, L) pour Conv1d
        x = x.transpose(1, 2)
        x = self.pool(self.activation(self.norm(self.conv(x))))
        return x.transpose(1, 2)  # Retour (B, L/2, D)


class Informer(nn.Module):
    """
    Modèle Informer pour la prévision de séries temporelles.
    
    Implémente :
    - ProbSparse Self-Attention (complexité O(L log L))
    - Distilling layers (compression progressive)
    - Positional encoding
    
    Basé sur : Zhou et al., "Informer: Beyond Efficient Transformer 
    for Long Sequence Time-Series Forecasting", AAAI 2021.
    """
    
    def __init__(
        self,
        input_size: int = len(TIMESERIES_CONFIG["features"]),
        d_model: int = INFORMER_CONFIG["d_model"],
        n_heads: int = INFORMER_CONFIG["n_heads"],
        e_layers: int = INFORMER_CONFIG["e_layers"],
        d_ff: int = INFORMER_CONFIG["d_ff"],
        dropout: float = INFORMER_CONFIG["dropout"],
        seq_len: int = TIMESERIES_CONFIG["input_days"],
        output_size: int = len(TIMESERIES_CONFIG["forecast_hours"]),
    ):
        super().__init__()
        self.d_model = d_model
        self.seq_len = seq_len
        
        # Input embedding
        self.input_proj = nn.Linear(input_size, d_model)
        
        # Positional encoding
        self.pos_encoding = self._generate_positional_encoding(seq_len, d_model)
        
        # Encoder layers avec distillation
        self.encoder_layers = nn.ModuleList()
        self.distilling_layers = nn.ModuleList()
        
        current_len = seq_len
        for i in range(e_layers):
            self.encoder_layers.append(
                InformerEncoderLayer(d_model, n_heads, d_ff, dropout)
            )
            if i < e_layers - 1:  # Pas de distillation après la dernière couche
                self.distilling_layers.append(DistillingLayer(d_model))
                current_len = current_len // 2
        
        # Output projection
        self.output_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(current_len * d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, output_size),
        )
        
        self.dropout = nn.Dropout(dropout)
    
    def _generate_positional_encoding(self, max_len: int, d_model: int) -> torch.Tensor:
        """Générer l'encodage positionnel sinusoïdal."""
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * -(math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        return pe.unsqueeze(0)  # (1, max_len, d_model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor (B, T, F) — séquence météo
            
        Returns:
            Tensor (B, output_size) — prédictions ET0 à 24h et 48h
        """
        B, T, F = x.shape
        
        # Input projection
        x = self.input_proj(x)  # (B, T, d_model)
        
        # Ajouter positional encoding
        pe = self.pos_encoding[:, :T, :].to(x.device)
        x = self.dropout(x + pe)
        
        # Encoder avec distillation
        for i, enc_layer in enumerate(self.encoder_layers):
            x = enc_layer(x)
            if i < len(self.distilling_layers):
                x = self.distilling_layers[i](x)
        
        # Output
        output = self.output_head(x)
        return output


# ═══════════════════════════════════════════════════════════
#  Factory
# ═══════════════════════════════════════════════════════════

def get_timeseries_model(model_type: str = "lstm", **kwargs) -> nn.Module:
    """
    Factory pour créer un modèle de séries temporelles.
    
    Args:
        model_type: "lstm", "gru", ou "informer"
    """
    if model_type == "lstm":
        return LSTMPredictor(**kwargs)
    elif model_type == "gru":
        return GRUPredictor(**kwargs)
    elif model_type == "informer":
        return Informer(**kwargs)
    else:
        raise ValueError(f"Modèle inconnu: {model_type}")


if __name__ == "__main__":
    print("=== Test Modèles Séries Temporelles ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    B, T, F = 4, 14, 5  # batch, timesteps (14 jours), features
    x = torch.randn(B, T, F).to(device)
    
    # Test LSTM
    lstm = LSTMPredictor().to(device)
    out_lstm = lstm(x)
    print(f"LSTM : input={x.shape} → output={out_lstm.shape}")
    
    # Test GRU
    gru = GRUPredictor().to(device)
    out_gru = gru(x)
    print(f"GRU  : input={x.shape} → output={out_gru.shape}")
    
    # Test Informer
    informer = Informer().to(device)
    out_inf = informer(x)
    print(f"Informer: input={x.shape} → output={out_inf.shape}")
    
    # Paramètres
    for name, model in [("LSTM", lstm), ("GRU", gru), ("Informer", informer)]:
        n = sum(p.numel() for p in model.parameters())
        print(f"  {name}: {n:,} paramètres")
    
    print("✅ Test séries temporelles réussi")
