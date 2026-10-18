# -*- coding: utf-8 -*-
"""训练 ESIM 实体规范化模型，产出 checkpoints/esim.pt。"""
import csv
import os
import random
import sys

import torch
import torch.nn as nn
import torch.optim as optim

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from log_utils import setup_log  # noqa: E402
from models.esim import ESIM, PAD, OOV  # noqa: E402

MAX_LEN = 20
EMBED_DIM = 100
HIDDEN_DIM = 128
EPOCHS = 20
BATCH = 128
LR = 1e-3
SEED = 42


def load_pairs(path):
    pairs = []
    with open(path, encoding="utf8") as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头 sentence1,sentence2,label
        for row in reader:
            if len(row) >= 3:
                pairs.append((row[0], row[1], int(row[2])))
    return pairs


def build_vocab(pairs):
    chars = set()
    for a, b, _ in pairs:
        chars.update(a)
        chars.update(b)
    word2id = {"<pad>": PAD, "<oov>": OOV}
    for i, ch in enumerate(sorted(chars)):
        word2id[ch] = i + 2
    return word2id


def encode(text, word2id):
    ids = [word2id.get(ch, OOV) for ch in text[:MAX_LEN]]
    ids += [PAD] * (MAX_LEN - len(ids))
    return ids


def accuracy(model, pairs, word2id):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for i in range(0, len(pairs), BATCH):
            batch = pairs[i:i + BATCH]
            x1 = torch.tensor([encode(a, word2id) for a, b, _ in batch], dtype=torch.long)
            x2 = torch.tensor([encode(b, word2id) for a, b, _ in batch], dtype=torch.long)
            y = torch.tensor([l for a, b, l in batch], dtype=torch.long)
            logits = model(x1, x2)
            correct += (logits.argmax(1) == y).sum().item()
            total += len(batch)
    return correct / total


def main():
    setup_log("train_esim")
    random.seed(SEED)
    torch.manual_seed(SEED)

    train_pairs = load_pairs(os.path.join(BASE_DIR, "data", "esim", "train.csv"))
    test_pairs = load_pairs(os.path.join(BASE_DIR, "data", "esim", "test.csv"))
    word2id = build_vocab(train_pairs + test_pairs)
    print("ESIM 训练样本 %d 条，测试样本 %d 条，字表大小 %d"
          % (len(train_pairs), len(test_pairs), len(word2id)))

    model = ESIM(len(word2id), EMBED_DIM, HIDDEN_DIM)
    opt = optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(EPOCHS):
        model.train()
        idx = list(range(len(train_pairs)))
        random.shuffle(idx)
        total = correct = 0
        loss_sum = 0.0
        for i in range(0, len(idx), BATCH):
            b = idx[i:i + BATCH]
            x1 = torch.tensor([encode(train_pairs[j][0], word2id) for j in b], dtype=torch.long)
            x2 = torch.tensor([encode(train_pairs[j][1], word2id) for j in b], dtype=torch.long)
            y = torch.tensor([train_pairs[j][2] for j in b], dtype=torch.long)
            opt.zero_grad()
            logits = model(x1, x2)
            loss = loss_fn(logits, y)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(b)
            correct += (logits.argmax(1) == y).sum().item()
            total += len(b)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print("epoch %02d/%d  train_acc=%.4f  loss=%.4f"
                  % (epoch + 1, EPOCHS, correct / total, loss_sum / total))

    test_acc = accuracy(model, test_pairs, word2id)
    print("TEST accuracy = %.4f" % test_acc)

    os.makedirs(os.path.join(BASE_DIR, "checkpoints"), exist_ok=True)
    ckpt = {
        "model_state": model.state_dict(),
        "word2id": word2id,
        "max_len": MAX_LEN,
        "vocab_size": len(word2id),
        "embed_dim": EMBED_DIM,
        "hidden_dim": HIDDEN_DIM,
    }
    torch.save(ckpt, os.path.join(BASE_DIR, "checkpoints", "esim.pt"))
    print("已保存 checkpoints/esim.pt")


if __name__ == "__main__":
    main()
