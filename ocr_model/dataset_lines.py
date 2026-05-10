import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import random

# ── Character Set ─────────────────────────────────────────────────
CHARS = " !\"#&'()*+,-./0123456789:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CHAR2IDX = {c: i+1 for i, c in enumerate(CHARS)}
IDX2CHAR = {i+1: c for i, c in enumerate(CHARS)}
IDX2CHAR[0] = ''
NUM_CLASSES = len(CHARS) + 1

IMG_HEIGHT = 64        # Higher resolution than before (was 32)
IMG_WIDTH = 512        # Wider for line-level images (was 128)
MAX_LABEL_LEN = 100    # Lines are longer than words

# ── Augmentation ──────────────────────────────────────────────────
class LineAugmentation:
    def __init__(self, is_train=True):
        self.is_train = is_train

    def elastic_distortion(self, image):
        if random.random() > 0.4:
            return image
        from scipy.ndimage import gaussian_filter
        h, w = image.shape[:2]
        alpha = w * 0.04
        sigma = w * 0.04
        dx = np.random.randn(h, w) * alpha
        dy = np.random.randn(h, w) * alpha
        dx = gaussian_filter(dx, sigma)
        dy = gaussian_filter(dy, sigma)
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (x + dx).astype(np.float32)
        map_y = (y + dy).astype(np.float32)
        return cv2.remap(image, map_x, map_y,
                        interpolation=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT)

    def __call__(self, image):
        if not self.is_train:
            return image
        # Random rotation (small for lines)
        if random.random() > 0.6:
            angle = random.uniform(-2, 2)
            h, w = image.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            image = cv2.warpAffine(image, M, (w, h),
                                   borderMode=cv2.BORDER_REPLICATE)
        # Random brightness/contrast
        if random.random() > 0.5:
            alpha = random.uniform(0.7, 1.3)
            beta = random.randint(-30, 30)
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        # Elastic distortion
        image = self.elastic_distortion(image)
        # Random noise
        if random.random() > 0.7:
            noise = np.random.randint(0, 15,
                                      image.shape, dtype=np.uint8)
            image = cv2.add(image, noise)
        return image

# ── Dataset ───────────────────────────────────────────────────────
class IAMLineDataset(Dataset):
    def __init__(self, labels_file, split='train'):
        self.split = split
        self.augment = LineAugmentation(is_train=(split == 'train'))
        self.samples = []
        self._load_samples(labels_file)

    def _load_samples(self, labels_file):
        all_samples = []
        with open(labels_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) != 2:
                    continue
                img_path, text = parts
                if not all(c in CHAR2IDX for c in text):
                    continue
                if len(text) > MAX_LABEL_LEN:
                    continue
                if len(text) < 2:
                    continue
                all_samples.append((img_path, text))

        random.seed(42)
        random.shuffle(all_samples)
        n = len(all_samples)

        if self.split == 'train':
            self.samples = all_samples[:int(0.88 * n)]
        elif self.split == 'val':
            self.samples = all_samples[int(0.88 * n):int(0.94 * n)]
        else:
            self.samples = all_samples[int(0.94 * n):]

        print(f"[{self.split}] Loaded {len(self.samples)} line samples")

    def _preprocess(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.ones((IMG_HEIGHT, IMG_WIDTH),
                         dtype=np.uint8) * 255

        img = self.augment(img)

        # Resize keeping aspect ratio
        h, w = img.shape
        new_w = min(IMG_WIDTH, int(w * IMG_HEIGHT / h))
        new_w = max(new_w, 1)
        img = cv2.resize(img, (new_w, IMG_HEIGHT))

        # Pad to fixed width
        padded = np.ones((IMG_HEIGHT, IMG_WIDTH),
                        dtype=np.uint8) * 255
        padded[:, :new_w] = img

        # Normalize to [-1, 1]
        img = padded.astype(np.float32) / 255.0
        img = (img - 0.5) / 0.5
        return torch.tensor(img).unsqueeze(0)

    def _encode(self, text):
        return [CHAR2IDX[c] for c in text]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, text = self.samples[idx]
        img = self._preprocess(img_path)
        encoded = self._encode(text)
        return (img,
                torch.tensor(encoded, dtype=torch.long),
                len(encoded),
                text)

def collate_fn(batch):
    images, labels, label_lens, raw = zip(*batch)
    images = torch.stack(images, 0)
    label_lens = torch.tensor(label_lens, dtype=torch.long)
    labels_padded = torch.zeros(
        len(labels), max(label_lens)).long()
    for i, lab in enumerate(labels):
        labels_padded[i, :len(lab)] = lab
    return images, labels_padded, label_lens, raw

def get_line_dataloaders(labels_file, batch_size=16):
    train_ds = IAMLineDataset(labels_file, 'train')
    val_ds   = IAMLineDataset(labels_file, 'val')
    test_ds  = IAMLineDataset(labels_file, 'test')

    train_loader = DataLoader(
        train_ds, batch_size=batch_size,
        shuffle=True, collate_fn=collate_fn,
        num_workers=0, pin_memory=True)
    val_loader = DataLoader(
        val_ds, batch_size=batch_size,
        shuffle=False, collate_fn=collate_fn,
        num_workers=0, pin_memory=True)
    test_loader = DataLoader(
        test_ds, batch_size=batch_size,
        shuffle=False, collate_fn=collate_fn,
        num_workers=0, pin_memory=True)

    return train_loader, val_loader, test_loader