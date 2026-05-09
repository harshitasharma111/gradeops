import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
import editdistance
import time
import json
from dataset import get_dataloaders, IDX2CHAR, NUM_CLASSES
from model import HTRModel, ctc_greedy_decode, ctc_beam_search_decode

# ── Config ─────────────────────────────────────────────────────────
CONFIG = {
    'data_root': r'C:\Users\Abhinav Chouhan\gradeops\ocr_data',
    'batch_size': 32,
    'num_epochs': 50,
    'lr': 3e-4,
    'hidden_size': 256,
    'num_lstm_layers': 2,
    'dropout': 0.3,
    'grad_clip': 5.0,
    'checkpoint_dir': 'ocr_model/checkpoints',
    'log_dir': 'ocr_model/logs',
    'save_every': 5,
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
}

# ── Metrics ────────────────────────────────────────────────────────
def compute_cer(predictions, targets):
    total_dist = 0
    total_len = 0
    for pred, tgt in zip(predictions, targets):
        total_dist += editdistance.eval(pred, tgt)
        total_len += len(tgt)
    return total_dist / max(total_len, 1)

def compute_wer(predictions, targets):
    total_dist = 0
    total_len = 0
    for pred, tgt in zip(predictions, targets):
        pred_words = pred.split()
        tgt_words = tgt.split()
        total_dist += editdistance.eval(pred_words, tgt_words)
        total_len += len(tgt_words)
    return total_dist / max(total_len, 1)

# ── Training Step ──────────────────────────────────────────────────
def train_epoch(model, loader, optimizer, criterion, device, epoch):
    model.train()
    total_loss = 0
    num_batches = 0
    start = time.time()

    for batch_idx, (images, labels, label_lens, raw_labels) in enumerate(loader):
        images = images.to(device)
        labels = labels.to(device)
        label_lens = label_lens.to(device)

        optimizer.zero_grad()

        log_probs = model(images)              # (T, B, C)
        T, B, C = log_probs.shape
        input_lens = torch.full((B,), T, dtype=torch.long).to(device)

        # Flatten labels for CTC
        labels_flat = []
        for i in range(B):
            labels_flat.append(labels[i, :label_lens[i]])
        labels_flat = torch.cat(labels_flat).to(device)

        loss = criterion(log_probs, labels_flat, input_lens, label_lens)

        if torch.isnan(loss) or torch.isinf(loss):
            print(f"  Skipping batch {batch_idx} - invalid loss")
            continue

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),
                                       CONFIG['grad_clip'])
        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

        if batch_idx % 50 == 0:
            elapsed = time.time() - start
            print(f"  Epoch {epoch} | Batch {batch_idx}/{len(loader)} "
                  f"| Loss: {loss.item():.4f} "
                  f"| Time: {elapsed:.1f}s")

    return total_loss / max(num_batches, 1)

# ── Validation Step ────────────────────────────────────────────────
def validate(model, loader, criterion, device, use_beam=False):
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    num_batches = 0

    with torch.no_grad():
        for images, labels, label_lens, raw_labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            label_lens = label_lens.to(device)

            log_probs = model(images)
            T, B, C = log_probs.shape
            input_lens = torch.full((B,), T,
                                    dtype=torch.long).to(device)

            labels_flat = []
            for i in range(B):
                labels_flat.append(labels[i, :label_lens[i]])
            labels_flat = torch.cat(labels_flat).to(device)

            loss = criterion(log_probs, labels_flat,
                           input_lens, label_lens)
            if not (torch.isnan(loss) or torch.isinf(loss)):
                total_loss += loss.item()
                num_batches += 1

            if use_beam:
                preds = ctc_beam_search_decode(
                    log_probs.cpu(), IDX2CHAR, beam_width=5)
            else:
                preds = ctc_greedy_decode(log_probs.cpu(), IDX2CHAR)

            all_preds.extend(preds)
            all_targets.extend(raw_labels)

    cer = compute_cer(all_preds, all_targets)
    wer = compute_wer(all_preds, all_targets)
    avg_loss = total_loss / max(num_batches, 1)

    # Show some examples
    print("\n  Sample predictions:")
    for i in range(min(5, len(all_preds))):
        print(f"    Target: '{all_targets[i]}' | "
              f"Pred: '{all_preds[i]}'")

    return avg_loss, cer, wer

# ── Main Training Loop ─────────────────────────────────────────────
def main():
    device = CONFIG['device']
    print(f"\n{'='*60}")
    print(f"Training HTR Model")
    print(f"Device: {device}")
    print(f"{'='*60}\n")

    os.makedirs(CONFIG['checkpoint_dir'], exist_ok=True)
    os.makedirs(CONFIG['log_dir'], exist_ok=True)

    # Data
    print("Loading dataset...")
    train_loader, val_loader, test_loader = get_dataloaders(
        CONFIG['data_root'], CONFIG['batch_size'])

    # Model
    model = HTRModel(
        num_classes=NUM_CLASSES,
        hidden_size=CONFIG['hidden_size'],
        num_lstm_layers=CONFIG['num_lstm_layers'],
        dropout=CONFIG['dropout']
    ).to(device)

    print(f"\nModel parameters: "
          f"{model.count_parameters():,}")

    # Loss - CTC
    criterion = nn.CTCLoss(blank=0, reduction='mean',
                           zero_infinity=True)

    # Optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=CONFIG['lr'],
        weight_decay=1e-4
    )

    # Scheduler - Cosine Annealing
    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=CONFIG['num_epochs'],
        eta_min=1e-6
    )

    # Training history
    history = {
        'train_loss': [], 'val_loss': [],
        'val_cer': [], 'val_wer': []
    }
    best_cer = float('inf')

    print("\nStarting training...\n")

    start_epoch = 1
    resume_path = os.path.join(CONFIG['checkpoint_dir'], 'checkpoint_epoch_10.pth')
    if os.path.exists(resume_path):
        print(f"Resuming from checkpoint...")
        ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        scheduler.load_state_dict(ckpt['scheduler_state_dict'])
        history = ckpt['history']
        start_epoch = ckpt['epoch'] + 1
        print(f"Resumed from epoch {ckpt['epoch']}")

    for epoch in range(start_epoch, CONFIG['num_epochs'] + 1):
        print(f"\n{'─'*50}")
        print(f"Epoch {epoch}/{CONFIG['num_epochs']} "
              f"| LR: {scheduler.get_last_lr()[0]:.6f}")
        print(f"{'─'*50}")

        # Train
        train_loss = train_epoch(
            model, train_loader, optimizer,
            criterion, device, epoch)

        # Validate
        use_beam = (epoch % 5 == 0)  # beam search every 5 epochs
        val_loss, val_cer, val_wer = validate(
            model, val_loader, criterion, device, use_beam)

        scheduler.step()

        # Log
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_cer'].append(val_cer)
        history['val_wer'].append(val_wer)

        print(f"\n  Train Loss: {train_loss:.4f} "
              f"| Val Loss: {val_loss:.4f} "
              f"| CER: {val_cer:.4f} "
              f"| WER: {val_wer:.4f}")

        # Save best model
        if val_cer < best_cer:
            best_cer = val_cer
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_cer': val_cer,
                'val_wer': val_wer,
                'config': CONFIG,
            }, os.path.join(CONFIG['checkpoint_dir'], 'best_model.pth'))
            print(f"  ✓ Saved best model (CER: {best_cer:.4f})")

        # Save checkpoint periodically
        if epoch % CONFIG['save_every'] == 0:
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'history': history,
            }, os.path.join(CONFIG['checkpoint_dir'],
                           f'checkpoint_epoch_{epoch}.pth'))

        # Save history
        with open(os.path.join(CONFIG['log_dir'],
                               'history.json'), 'w') as f:
            json.dump(history, f, indent=2)

    # Final test evaluation
    print(f"\n{'='*60}")
    print("Final Test Evaluation")
    print(f"{'='*60}")

    # Load best model
    ckpt = torch.load(
        os.path.join(CONFIG['checkpoint_dir'], 'best_model.pth'),
        map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])

    test_loss, test_cer, test_wer = validate(
        model, test_loader, criterion, device, use_beam=True)

    print(f"\nTest CER: {test_cer:.4f} ({test_cer*100:.2f}%)")
    print(f"Test WER: {test_wer:.4f} ({test_wer*100:.2f}%)")
    print(f"Best Val CER: {best_cer:.4f} ({best_cer*100:.2f}%)")

    # Save final results
    results = {
        'test_cer': test_cer,
        'test_wer': test_wer,
        'best_val_cer': best_cer,
        'total_epochs': CONFIG['num_epochs'],
        'model_parameters': model.count_parameters(),
    }
    with open(os.path.join(CONFIG['log_dir'],
                           'final_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    print("\nTraining complete!")
    print(f"Best model saved at: "
          f"{CONFIG['checkpoint_dir']}/best_model.pth")

if __name__ == '__main__':
    main()