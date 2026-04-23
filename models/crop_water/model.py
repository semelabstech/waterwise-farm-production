"""
Crop Water MLP Model — Predicts daily ETc (mm/day) for any crop.

Uses crop Kc coefficient, local ET0, and climate features to predict
precise water requirements using FAO-56 methodology enhanced with AI.
"""
import torch
import torch.nn as nn


class CropWaterMLP(nn.Module):
    """
    Multi-Layer Perceptron pour predire l'ETc journalier (mm/jour).

    Inputs (8 features):
        - kc_stage: Kc coefficient at current growth stage
        - et0: Reference evapotranspiration (mm/day)
        - temperature: Air temperature (C)
        - humidity: Relative humidity (%)
        - wind_speed: Wind speed (m/s)
        - solar_radiation: Solar radiation (MJ/m2/day)
        - soil_type: Encoded soil type (0-5)
        - growth_fraction: Current day / total growing days (0-1)

    Output (1):
        - etc_predicted: Predicted crop evapotranspiration (mm/day)
    """

    def __init__(self, input_dim=8, hidden_dims=None, dropout=0.2):
        super(CropWaterMLP, self).__init__()
        if hidden_dims is None:
            hidden_dims = [128, 64, 32]

        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = h_dim

        layers.append(nn.Linear(prev_dim, 1))
        layers.append(nn.ReLU())  # ETc is always positive

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x).squeeze(-1)
