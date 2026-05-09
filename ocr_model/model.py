import torch
import torch.nn as nn
import torch.nn.functional as F
from dataset import NUM_CLASSES

# ── Residual Block ─────────────────────────────────────────────────
class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.skip = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.skip = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1,
                          stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + self.skip(x)
        return F.relu(out)

# ── CNN Feature Extractor ──────────────────────────────────────────
class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),                          # H/2, W/2

            # Block 2 - Residual
            ResidualBlock(32, 64),
            nn.MaxPool2d(2, 2),                          # H/4, W/4

            # Block 3 - Residual
            ResidualBlock(64, 128),
            ResidualBlock(128, 128),
            nn.MaxPool2d((2, 1), (2, 1)),                # H/8, W/4

            # Block 4 - Residual
            ResidualBlock(128, 256),
            ResidualBlock(256, 256),
            nn.MaxPool2d((2, 1), (2, 1)),                # H/16, W/4

            # Block 5
            nn.Conv2d(256, 512, 3, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1), (2, 1)),                # H/32, W/4

            nn.Dropout2d(0.25),
        )

    def forward(self, x):
        return self.features(x)

# ── Attention Mechanism ────────────────────────────────────────────
class TemporalAttention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size * 2, 1)

    def forward(self, lstm_out):
        # lstm_out: (T, B, hidden*2)
        scores = self.attn(lstm_out)           # (T, B, 1)
        weights = torch.softmax(scores, dim=0) # (T, B, 1)
        return lstm_out * weights              # weighted

# ── Full HTR Model ─────────────────────────────────────────────────
class HTRModel(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES, hidden_size=256,
                 num_lstm_layers=2, dropout=0.3):
        super().__init__()
        self.cnn = CNN()
        # CNN output: (B, 512, 1, W') -> we'll squeeze height
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, None))

        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=512,
            hidden_size=hidden_size,
            num_layers=num_lstm_layers,
            batch_first=False,
            bidirectional=True,
            dropout=dropout if num_lstm_layers > 1 else 0
        )

        self.attention = TemporalAttention(hidden_size)
        self.dropout = nn.Dropout(dropout)

        # Output projection
        self.fc = nn.Linear(hidden_size * 2, num_classes)

        self._init_weights()

    def _init_weights(self):
        for name, param in self.named_parameters():
            if 'lstm' in name:
                if 'weight' in name:
                    nn.init.orthogonal_(param)
                elif 'bias' in name:
                    nn.init.zeros_(param)
            elif 'fc' in name:
                if 'weight' in name:
                    nn.init.xavier_uniform_(param)

    def forward(self, x):
        # x: (B, 1, H, W)
        features = self.cnn(x)                 # (B, 512, 1, W')
        features = self.adaptive_pool(features) # (B, 512, 1, W')
        B, C, H, W = features.shape
        features = features.squeeze(2)          # (B, 512, W')
        features = features.permute(2, 0, 1)   # (W', B, 512) = (T, B, C)

        # BiLSTM
        lstm_out, _ = self.lstm(features)      # (T, B, hidden*2)
        lstm_out = self.attention(lstm_out)    # weighted
        lstm_out = self.dropout(lstm_out)

        # Classify each timestep
        logits = self.fc(lstm_out)             # (T, B, num_classes)
        log_probs = F.log_softmax(logits, dim=2)
        return log_probs

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ── CTC Beam Search Decoder ────────────────────────────────────────
def ctc_greedy_decode(log_probs, idx2char):
    # log_probs: (T, B, C)
    pred_indices = torch.argmax(log_probs, dim=2)  # (T, B)
    pred_indices = pred_indices.permute(1, 0)       # (B, T)
    results = []
    for seq in pred_indices:
        chars = []
        prev = -1
        for idx in seq:
            idx = idx.item()
            if idx != 0 and idx != prev:
                if idx in idx2char and idx2char[idx]:
                    chars.append(idx2char[idx])
            prev = idx
        results.append(''.join(chars))
    return results


def ctc_beam_search_decode(log_probs, idx2char, beam_width=5):
    # log_probs: (T, B, C)
    T, B, C = log_probs.shape
    results = []
    probs = torch.exp(log_probs)

    for b in range(B):
        # beams: list of (score, sequence)
        beams = [(0.0, [])]
        for t in range(T):
            new_beams = {}
            for score, seq in beams:
                for c in range(C):
                    p = probs[t, b, c].item()
                    if p < 1e-6:
                        continue
                    new_score = score + torch.log(
                        probs[t, b, c] + 1e-10).item()
                    # CTC collapse
                    if c == 0:
                        key = tuple(seq)
                    elif seq and seq[-1] == c:
                        key = tuple(seq)
                    else:
                        key = tuple(seq + [c])
                    if key not in new_beams:
                        new_beams[key] = new_score
                    else:
                        new_beams[key] = max(
                            new_beams[key], new_score)
            # Keep top beams
            beams = sorted(new_beams.items(),
                          key=lambda x: x[1],
                          reverse=True)[:beam_width]
            beams = [(score, list(seq)) for seq, score in beams]

        best_seq = beams[0][1] if beams else []
        text = ''.join(idx2char.get(c, '') for c in best_seq
                      if idx2char.get(c, ''))
        results.append(text)
    return results