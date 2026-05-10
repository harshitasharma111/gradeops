import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
import editdistance
import time
import json
import math

from dataset_lines import get_line_dataloaders, IDX2CHAR, NUM_CLASSES
from model_v2 import HTRModelV2, ctc_greedy_decode, ctc_beam_search_decode

CONFIG = {
    'labels_file': r'C:\Users\Abhinav Chouhan\gradeops\ocr_data\iam_lines\lines.txt',
    'batch_size': 8,
    'num_epochs': 100,
    'lr': 3e-4,
    'warmup_epochs': 5,
    'hidden_size': 512,
    'num_lstm_layers': 3,
    'dropout': 0.3,
    'grad_clip': 5.0,
    'checkpoint_dir': 'ocr_model/checkpoints_v2',
    'log_dir': 'ocr_model/logs_v2',
    'save_every': 10,
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
}

def compute_cer(predictions, targets):
    total_dist, total_len = 0, 0
    for p, t in zip(predictions, targets):
        total_dist += editdistance.eval(p, t)
        total_len  += len(t)
    return total_dist / max(total_len, 1)

def compute_wer(predictions, targets):
    total_dist, total_len = 0, 0
    for p, t in zip(predictions, targets):
        total_dist += editdistance.eval(p.split(), t.split())
        total_len  += len(t.split())
    return total_dist / max(total_len, 1)

def warmup_lr(epoch, warmup_epochs, base_lr):
    if epoch < warmup_epochs:
        return base_lr * (epoch + 1) / warmup_epochs
    return base_lr

def train_epoch(model, loader, optimizer, criterion, device, epoch):
    model.train()
    total_loss, num_batches = 0, 0
    start = time.time()

    for batch_idx, (images, labels, label_lens, raw) in enumerate(loader):
        images    = images.to(device)
        labels    = labels.to(device)
        label_lens = label_lens.to(device)

        optimizer.zero_grad()
        log_probs = model(images)
        T, B, C   = log_probs.shape
        input_lens = torch.full((B,), T, dtype=torch.long).to(device)

        labels_flat = torch.cat([
            labels[i, :label_lens[i]] for i in range(B)
        ]).to(device)

        loss = criterion(log_probs, labels_flat,
                        input_lens, label_lens)

        if torch.isnan(loss) or torch.isinf(loss):
            continue

        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            model.parameters(), CONFIG['grad_clip'])
        optimizer.step()

        total_loss  += loss.item()
        num_batches += 1

        if batch_idx % 30 == 0:
            print(f"  Epoch {epoch} | Batch {batch_idx}/{len(loader)}"
                  f" | Loss: {loss.item():.4f}"
                  f" | Time: {time.time()-start:.1f}s")

    return total_loss / max(num_batches, 1)

def validate(model, loader, criterion, device, use_beam=False):
    model.eval()
    total_loss, num_batches = 0, 0
    all_preds, all_targets  = [], []

    with torch.no_grad():
        for images, labels, label_lens, raw in loader:
            images     = images.to(device)
            labels     = labels.to(device)
            label_lens = label_lens.to(device)

            log_probs  = model(images)
            T, B, C    = log_probs.shape
            input_lens = torch.full(
                (B,), T, dtype=torch.long).to(device)

            labels_flat = torch.cat([
                labels[i, :label_lens[i]] for i in range(B)
            ]).to(device)

            loss = criterion(log_probs, labels_flat,
                           input_lens, label_lens)
            if not (torch.isnan(loss) or torch.isinf(loss)):
                total_loss  += loss.item()
                num_batches += 1

            if use_beam:
                preds = ctc_beam_search_decode(
                    log_probs.cpu(), IDX2CHAR, beam_width=10)
            else:
                preds = ctc_greedy_decode(log_probs.cpu(), IDX2CHAR)

            all_preds.extend(preds)
            all_targets.extend(raw)

    cer = compute_cer(all_preds, all_targets)
    wer = compute_wer(all_preds, all_targets)

    print("\n  Sample predictions:")
    for i in range(min(5, len(all_preds))):
        print(f"    Target: '{all_targets[i]}'")
        print(f"    Pred:   '{all_preds[i]}'")
        print()

    return total_loss / max(num_batches, 1), cer, wer

def main():
    device = CONFIG['device']
    print(f"\n{'='*60}")
    print(f"Training HTR Model V2 — Line Level")
    print(f"Device: {device}")
    print(f"{'='*60}\n")

    os.makedirs(CONFIG['checkpoint_dir'], exist_ok=True)
    os.makedirs(CONFIG['log_dir'], exist_ok=True)

    print("Loading dataset...")
    train_loader, val_loader, test_loader = get_line_dataloaders(
        CONFIG['labels_file'], CONFIG['batch_size'])

    model = HTRModelV2(
        num_classes=NUM_CLASSES,
        hidden_size=CONFIG['hidden_size'],
        num_lstm_layers=CONFIG['num_lstm_layers'],
        dropout=CONFIG['dropout']
    ).to(device)

    print(f"\nModel V2 parameters: {model.count_parameters():,}")

    criterion = nn.CTCLoss(blank=0, reduction='mean',
                           zero_infinity=True)
    optimizer = optim.AdamW(
        model.parameters(),
        lr=CONFIG['lr'],
        weight_decay=1e-4,
        betas=(0.9, 0.999)
    )

    # Cosine Annealing with Warm Restarts
    scheduler = CosineAnnealingWarmRestarts(
        optimizer, T_0=20, T_mult=2, eta_min=1e-6)

    history  = {'train_loss': [], 'val_loss': [],
                'val_cer': [], 'val_wer': []}
    best_cer = float('inf')

    # Check for existing checkpoint to resume
    resume_path = os.path.join(
        CONFIG['checkpoint_dir'], 'latest.pth')
    start_epoch = 1
    if os.path.exists(resume_path):
        print("Resuming from checkpoint...")
        ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        scheduler.load_state_dict(ckpt['scheduler_state_dict'])
        history     = ckpt['history']
        start_epoch = ckpt['epoch'] + 1
        best_cer    = ckpt.get('best_cer', float('inf'))
        print(f"Resumed from epoch {ckpt['epoch']}")

    print(f"\nStarting training from epoch {start_epoch}...\n")

    for epoch in range(start_epoch, CONFIG['num_epochs'] + 1):
        # Warmup
        if epoch <= CONFIG['warmup_epochs']:
            lr = warmup_lr(epoch-1, CONFIG['warmup_epochs'],
                          CONFIG['lr'])
            for pg in optimizer.param_groups:
                pg['lr'] = lr

        print(f"\n{'─'*55}")
        print(f"Epoch {epoch}/{CONFIG['num_epochs']}"
              f" | LR: {optimizer.param_groups[0]['lr']:.6f}")
        print(f"{'─'*55}")

        train_loss = train_epoch(
            model, train_loader, optimizer,
            criterion, device, epoch)

        use_beam = (epoch % 5 == 0 or epoch == 1)
        val_loss, val_cer, val_wer = validate(
            model, val_loader, criterion, device, use_beam)

        if epoch > CONFIG['warmup_epochs']:
            scheduler.step()

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_cer'].append(val_cer)
        history['val_wer'].append(val_wer)

        print(f"\n  Train Loss: {train_loss:.4f}"
              f" | Val Loss: {val_loss:.4f}"
              f" | CER: {val_cer:.4f}"
              f" | WER: {val_wer:.4f}")

        # Save best
        if val_cer < best_cer:
            best_cer = val_cer
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_cer': val_cer,
                'val_wer': val_wer,
                'config': CONFIG,
            }, os.path.join(CONFIG['checkpoint_dir'],
                           'best_model_v2.pth'))
            print(f"  ✓ Best model saved (CER: {best_cer:.4f})")

        # Save latest for resuming
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'history': history,
            'best_cer': best_cer,
        }, os.path.join(CONFIG['checkpoint_dir'], 'latest.pth'))

        with open(os.path.join(CONFIG['log_dir'],
                               'history_v2.json'), 'w') as f:
            json.dump(history, f, indent=2)

    # Final test
    print(f"\n{'='*60}")
    print("Final Test Evaluation")
    ckpt = torch.load(
        os.path.join(CONFIG['checkpoint_dir'], 'best_model_v2.pth'),
        map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    test_loss, test_cer, test_wer = validate(
        model, test_loader, criterion, device, use_beam=True)

    print(f"\nTest CER: {test_cer:.4f} ({test_cer*100:.2f}%)")
    print(f"Test WER: {test_wer:.4f} ({test_wer*100:.2f}%)")
    print(f"Best Val CER: {best_cer:.4f} ({best_cer*100:.2f}%)")

    results = {
        'test_cer': test_cer, 'test_wer': test_wer,
        'best_val_cer': best_cer,
        'total_epochs': CONFIG['num_epochs'],
        'model_parameters': model.count_parameters(),
        'architecture': 'CNN+BiLSTM+MultiHeadAttention+CTC',
        'training_data': 'IAM Line Level',
    }
    with open(os.path.join(CONFIG['log_dir'],
                           'final_results_v2.json'), 'w') as f:
        json.dump(results, f, indent=2)

    print("\nTraining V2 complete!")

if __name__ == '__main__':
    main()