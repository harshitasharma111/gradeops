import torch
import torch.nn as nn
import torch.nn.functional as F
from dataset_lines import NUM_CLASSES, IDX2CHAR

# ── Residual Block ─────────────────────────────────────────────────
class ResidualBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3,
                               stride=stride, padding=1, bias=False)
        self.bn1   = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3,
                               padding=1, bias=False)
        self.bn2   = nn.BatchNorm2d(out_ch)
        self.skip  = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.skip = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 1,
                          stride=stride, bias=False),
                nn.BatchNorm2d(out_ch)
            )

    def forward(self, x):
        out = F.gelu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return F.gelu(out + self.skip(x))

# ── Deeper CNN ─────────────────────────────────────────────────────
class DeepCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            # Stem
            nn.Conv2d(1, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.GELU(),

            # Block 1
            ResidualBlock(32, 64),
            nn.MaxPool2d(2, 2),               # 32x256

            # Block 2
            ResidualBlock(64, 128),
            ResidualBlock(128, 128),
            nn.MaxPool2d(2, 2),               # 16x128

            # Block 3
            ResidualBlock(128, 256),
            ResidualBlock(256, 256),
            nn.MaxPool2d((2, 1), (2, 1)),     # 8x128

            # Block 4
            ResidualBlock(256, 512),
            ResidualBlock(512, 512),
            nn.MaxPool2d((2, 1), (2, 1)),     # 4x128

            # Block 5
            ResidualBlock(512, 512),
            nn.MaxPool2d((2, 1), (2, 1)),     # 2x128

            # Block 6
            nn.Conv2d(512, 512, (2, 1),
                      padding=0, bias=False),  # 1x128
            nn.BatchNorm2d(512),
            nn.GELU(),

            nn.Dropout2d(0.2),
        )

    def forward(self, x):
        return self.features(x)

# ── Multi-Head Self Attention on sequence ─────────────────────────
class SequenceAttention(nn.Module):
    def __init__(self, hidden_size, num_heads=8):
        super().__init__()
        self.attn = nn.MultiheadAttention(
            hidden_size * 2, num_heads,
            dropout=0.1, batch_first=False)
        self.norm = nn.LayerNorm(hidden_size * 2)

    def forward(self, x):
        # x: (T, B, H)
        attended, _ = self.attn(x, x, x)
        return self.norm(x + attended)

# ── HTR Model V2 ───────────────────────────────────────────────────
class HTRModelV2(nn.Module):
    def __init__(self,
                 num_classes=NUM_CLASSES,
                 hidden_size=512,
                 num_lstm_layers=3,
                 dropout=0.3):
        super().__init__()
        self.cnn = DeepCNN()
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, None))

        # Bigger BiLSTM — 3 layers, 512 hidden
        self.lstm = nn.LSTM(
            input_size=512,
            hidden_size=hidden_size,
            num_layers=num_lstm_layers,
            batch_first=False,
            bidirectional=True,
            dropout=dropout
        )

        # Multi-head attention on LSTM output
        self.attention = SequenceAttention(hidden_size, num_heads=8)
        self.dropout   = nn.Dropout(dropout)

        # Layer norm before projection
        self.layer_norm = nn.LayerNorm(hidden_size * 2)

        # Output
        self.fc = nn.Linear(hidden_size * 2, num_classes)
        self._init_weights()

    def _init_weights(self):
        for name, param in self.named_parameters():
            if 'lstm' in name and 'weight' in name:
                nn.init.orthogonal_(param)
            elif 'lstm' in name and 'bias' in name:
                nn.init.zeros_(param)
            elif 'fc.weight' in name:
                nn.init.xavier_uniform_(param)

    def forward(self, x):
        # x: (B, 1, H, W)
        feat = self.cnn(x)                     # (B, 512, 1, W')
        feat = self.adaptive_pool(feat)
        B, C, H, W = feat.shape
        feat = feat.squeeze(2).permute(2, 0, 1)  # (T, B, 512)

        lstm_out, _ = self.lstm(feat)          # (T, B, 1024)
        attended    = self.attention(lstm_out) # (T, B, 1024)
        normed      = self.layer_norm(attended)
        dropped     = self.dropout(normed)

        logits    = self.fc(dropped)           # (T, B, C)
        log_probs = F.log_softmax(logits, dim=2)
        return log_probs

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters()
                   if p.requires_grad)

# ── Decoders ───────────────────────────────────────────────────────
def ctc_greedy_decode(log_probs, idx2char):
    pred = torch.argmax(log_probs, dim=2).permute(1, 0)
    results = []
    for seq in pred:
        chars, prev = [], -1
        for idx in seq:
            idx = idx.item()
            if idx != 0 and idx != prev:
                c = idx2char.get(idx, '')
                if c:
                    chars.append(c)
            prev = idx
        results.append(''.join(chars))
    return results

def ctc_beam_search_decode(log_probs, idx2char, beam_width=10):
    T, B, C = log_probs.shape
    probs   = torch.exp(log_probs)
    results = []

    for b in range(B):
        beams = [(0.0, [])]
        for t in range(T):
            new_beams = {}
            for score, seq in beams:
                for c in range(C):
                    p = probs[t, b, c].item()
                    if p < 1e-7:
                        continue
                    ns = score + torch.log(
                        probs[t, b, c] + 1e-10).item()
                    if c == 0:
                        key = tuple(seq)
                    elif seq and seq[-1] == c:
                        key = tuple(seq)
                    else:
                        key = tuple(seq + [c])
                    new_beams[key] = max(
                        new_beams.get(key, -1e9), ns)
            beams = sorted(new_beams.items(),
                          key=lambda x: x[1],
                          reverse=True)[:beam_width]
            beams = [(s, list(k)) for k, s in beams]

        best = beams[0][1] if beams else []
        text = ''.join(idx2char.get(c, '')
                      for c in best if idx2char.get(c, ''))
        results.append(text)
    return results