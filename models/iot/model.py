import torch
import torch.nn as nn

class IoTAnomalyDetector(nn.Module):
    """
    LSTM-based Autoencoder for detecting anomalies in IoT sensor datastreams.
    Takes sequences of (soil_moisture, temperature, humidity, precipitation).
    If the reconstruction error is abnormally high, it signals an anomaly.
    """
    def __init__(self, input_dim=4, hidden_dim=64, latent_dim=16):
        super(IoTAnomalyDetector, self).__init__()
        
        # Encoder
        self.encoder_lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, num_layers=1)
        self.encoder_fc = nn.Linear(hidden_dim, latent_dim)
        self.encoder_activation = nn.ReLU()
        
        # Decoder
        self.decoder_fc = nn.Linear(latent_dim, hidden_dim)
        self.decoder_lstm = nn.LSTM(hidden_dim, input_dim, batch_first=True, num_layers=1)
        
    def forward(self, x):
        """
        x: (batch_size, seq_len, input_dim)
        """
        seq_len = x.size(1)
        
        # ENCODE
        enc_out, (h_n, c_n) = self.encoder_lstm(x)
        # Use the hidden state of the last time step
        z = self.encoder_activation(self.encoder_fc(h_n[-1])) # (batch_size, latent_dim)
        
        # DECODE
        dec_init = self.encoder_activation(self.decoder_fc(z)) # (batch_size, hidden_dim)
        # Repeat for the length of the sequence
        dec_in = dec_init.unsqueeze(1).repeat(1, seq_len, 1) # (batch_size, seq_len, hidden_dim)
        
        dec_out, _ = self.decoder_lstm(dec_in) # (batch_size, seq_len, input_dim)
        return dec_out
