# -*- coding: utf-8 -*-
"""训练字符级 TextCNN 意图分类器，产出 checkpoints/intent.pt。"""
import csv
import os
import random
import sys

import torch
import torch.nn as nn
import torch.optim as optim

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from models.intent_textcnn import TextCNN, PAD, OOV  # noqa: E402

LABELS = [
    "event_ports", "event_person", "ship_mission", "events_by_country",
    "ports_by_country", "country_of_port", "other",
]
MAX_LEN = 40
EMBED_DIM = 100
FILTERS = 128
EPOCHS = 30
BATCH = 64
LR = 1e-3
SEED = 42


def load_data(path):
    rows = []
    with open(path, encoding="utf8") as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        for row in reader:
            if len(row) >= 2:
                rows.append((row[0], row[1]))
    return rows


def build_vocab(texts):
    chars = set()
    for t in texts:
        chars.update(t)
    word2id = {"<pad>": PAD, "<oov>": OOV}
    for i, ch in enumerate(sorted(chars)):
        word2id[ch] = i + 2
    return word2id


def encode(text, word2id):
    ids = [word2id.get(ch, OOV) for ch in text[:MAX_LEN]]
    ids += [PAD] * (MAX_LEN - len(ids))
    return ids


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)

    train_rows = load_data(os.path.join(BASE_DIR, "data", "intent", "train.csv"))
    test_rows = load_data(os.path.join(BASE_DIR, "data", "intent", "test.csv"))
    word2id = build_vocab([r[0] for r in train_rows] + [r[0] for r in test_rows])
    label2id = {l: i for i, l in enumerate(LABELS)}

    model = TextCNN(len(word2id), EMBED_DIM, len(LABELS), filters=FILTERS)
    opt = optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    train_x = torch.tensor([encode(r[0], word2id) for r in train_rows], dtype=torch.long)
    train_y = torch.tensor([label2id[r[1]] for r in train_rows], dtype=torch.long)
    test_x = torch.tensor([encode(r[0], word2id) for r in test_rows], dtype=torch.long)
    test_y = torch.tensor([label2id[r[1]] for r in test_rows], dtype=torch.long)

    for epoch in range(EPOCHS):
        model.train()
        idx = list(range(len(train_x)))
        random.shuffle(idx)
        total = 0
        correct = 0
        loss_sum = 0.0
        for i in range(0, len(idx), BATCH):
            b = idx[i:i + BATCH]
            xb, yb = train_x[b], train_y[b]
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(b)
            correct += (logits.argmax(1) == yb).sum().item()
            total += len(b)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print("epoch %02d/%d  train_acc=%.4f  loss=%.4f"
                  % (epoch + 1, EPOCHS, correct / total, loss_sum / total))

    model.eval()
    with torch.no_grad():
        pred = model(test_x).argmax(1)
        acc = (pred == test_y).float().mean().item()
    print("TEST accuracy = %.4f" % acc)

    os.makedirs(os.path.join(BASE_DIR, "checkpoints"), exist_ok=True)
    ckpt = {
        "model_state": model.state_dict(),
        "word2id": word2id,
        "id2label": LABELS,
        "max_len": MAX_LEN,
        "vocab_size": len(word2id),
        "embed_dim": EMBED_DIM,
        "filters": FILTERS,
    }
    torch.save(ckpt, os.path.join(BASE_DIR, "checkpoints", "intent.pt"))
    print("已保存 checkpoints/intent.pt")


if __name__ == "__main__":
    main()
