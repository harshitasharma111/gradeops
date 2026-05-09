import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as transforms
from torchvision.transforms import functional as F
import random

# ── Character Set ─────────────────────────────────────────────────
CHARS = " !\"#&'()*+,-./0123456789:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CHAR2IDX = {c: i+1 for i, c in enumerate(CHARS)}  # 0 reserved for blank (CTC)
IDX2CHAR = {i+1: c for i, c in enumerate(CHARS)}
IDX2CHAR[0] = ''  # blank token
NUM_CLASSES = len(CHARS) + 1  # +1 for CTC blank

IMG_HEIGHT = 32
IMG_WIDTH = 128

# ── Augmentation ──────────────────────────────────────────────────
class HandwritingAugmentation:
    def __init__(self, is_train=True):
        self.is_train = is_train

    def elastic_distortion(self, image):
        if random.random() > 0.5:
            return image
        h, w = image.shape[:2]
        alpha = w * 0.05
        sigma = w * 0.05
        dx = np.random.randn(h, w) * alpha
        dy = np.random.randn(h, w) * alpha
        from scipy.ndimage import gaussian_filter, map_coordinates
        dx = gaussian_filter(dx, sigma)
        dy = gaussian_filter(dy, sigma)
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (x + dx).astype(np.float32)
        map_y = (y + dy).astype(np.float32)
        distorted = cv2.remap(image, map_x, map_y,
                              interpolation=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REFLECT)
        return distorted

    def __call__(self, image):
        if not self.is_train:
            return image
        # Random rotation
        if random.random() > 0.5:
            angle = random.uniform(-5, 5)
            h, w = image.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            image = cv2.warpAffine(image, M, (w, h),
                                   borderMode=cv2.BORDER_REPLICATE)
        # Random brightness/contrast
        if random.random() > 0.5:
            alpha = random.uniform(0.8, 1.2)
            beta = random.randint(-20, 20)
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        # Elastic distortion
        image = self.elastic_distortion(image)
        # Random perspective
        if random.random() > 0.7:
            h, w = image.shape[:2]
            margin = int(w * 0.05)
            pts1 = np.float32([[0,0],[w,0],[0,h],[w,h]])
            pts2 = np.float32([
                [random.randint(0, margin), random.randint(0, margin)],
                [w - random.randint(0, margin), random.randint(0, margin)],
                [random.randint(0, margin), h - random.randint(0, margin)],
                [w - random.randint(0, margin), h - random.randint(0, margin)]
            ])
            M = cv2.getPerspectiveTransform(pts1, pts2)
            image = cv2.warpPerspective(image, M, (w, h),
                                        borderMode=cv2.BORDER_REPLICATE)
        return image

# ── Dataset ───────────────────────────────────────────────────────
class IAMDataset(Dataset):
    def __init__(self, data_root, split='train', max_label_len=32):
        self.data_root = data_root
        self.split = split
        self.max_label_len = max_label_len
        self.augment = HandwritingAugmentation(is_train=(split == 'train'))
        self.samples = []
        self._load_samples()

    def _load_samples(self):
        words_file = os.path.join(self.data_root, 'iam_words', 'words.txt')
        words_dir = os.path.join(self.data_root, 'iam_words', 'words')

        valid_samples = []
        with open(words_file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split(' ')
                if len(parts) < 9:
                    continue
                word_id = parts[0]
                seg_result = parts[1]
                if seg_result == 'err':
                    continue
                label = ' '.join(parts[8:])
                # Filter out labels with unknown characters
                if not all(c in CHAR2IDX for c in label):
                    continue
                if len(label) > self.max_label_len:
                    continue
                # Build image path: a01-000u-00-00 -> words/a01/a01-000u/a01-000u-00-00.png
                parts_id = word_id.split('-')
                img_path = os.path.join(
                    words_dir,
                    parts_id[0],
                    f"{parts_id[0]}-{parts_id[1]}",
                    f"{word_id}.png"
                )
                if os.path.exists(img_path):
                    valid_samples.append((img_path, label))

        # Split: 90% train, 5% val, 5% test
        random.seed(42)
        random.shuffle(valid_samples)
        n = len(valid_samples)
        if self.split == 'train':
            self.samples = valid_samples[:int(0.9 * n)]
        elif self.split == 'val':
            self.samples = valid_samples[int(0.9 * n):int(0.95 * n)]
        else:
            self.samples = valid_samples[int(0.95 * n):]

        print(f"[{self.split}] Loaded {len(self.samples)} samples")

    def _preprocess(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.ones((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8) * 255
        img = self.augment(img)
        # Resize keeping aspect ratio
        h, w = img.shape
        new_w = min(IMG_WIDTH, int(w * IMG_HEIGHT / h))
        img = cv2.resize(img, (new_w, IMG_HEIGHT))
        # Pad to fixed width
        padded = np.ones((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8) * 255
        padded[:, :new_w] = img
        # Normalize
        img = padded.astype(np.float32) / 255.0
        img = (img - 0.5) / 0.5  # [-1, 1]
        img = torch.tensor(img).unsqueeze(0)  # (1, H, W)
        return img

    def _encode_label(self, label):
        return [CHAR2IDX[c] for c in label]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = self._preprocess(img_path)
        encoded = self._encode_label(label)
        return img, torch.tensor(encoded, dtype=torch.long), len(encoded), label

def collate_fn(batch):
    images, labels, label_lens, raw_labels = zip(*batch)
    images = torch.stack(images, 0)
    label_lens = torch.tensor(label_lens, dtype=torch.long)
    labels_padded = torch.zeros(len(labels), max(label_lens)).long()
    for i, lab in enumerate(labels):
        labels_padded[i, :len(lab)] = lab
    return images, labels_padded, label_lens, raw_labels

def get_dataloaders(data_root, batch_size=32):
    train_ds = IAMDataset(data_root, split='train')
    val_ds = IAMDataset(data_root, split='val')
    test_ds = IAMDataset(data_root, split='test')
    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              shuffle=True, collate_fn=collate_fn,
                              num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size,
                            shuffle=False, collate_fn=collate_fn,
                            num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size,
                             shuffle=False, collate_fn=collate_fn,
                             num_workers=0, pin_memory=True)
    return train_loader, val_loader, test_loader