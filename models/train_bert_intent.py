# -*- coding: utf-8 -*-
"""训练 BERT + TextCNN 意图分类器，产出 checkpoints/bert_intent.pt。

前置条件（缺一不可）：
  1. 安装 transformers：  pip install transformers
  2. 可获取中文 BERT 权重（bert-base-chinese）。首次运行会自动从 HuggingFace
     下载到缓存；若网络受限，可手动下载到本地目录并设置环境变量：

         Windows PowerShell:  $env:BERT_MODEL_DIR = "D:\\bert-base-chinese"
         Git Bash / Linux:    export BERT_MODEL_DIR=/path/to/bert-base-chinese

     本地目录需包含 config.json、pytorch_model.bin（或 model.safetensors）、
     vocab.txt、tokenizer.json 等文件（HuggingFace 标准结构）。
"""
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

try:
    from transformers import AutoTokenizer, BertModel
    _HAS_TRANSFORMERS = True
except Exception:  # pragma: no cover
    _HAS_TRANSFORMERS = False

LABELS = [
    "event_ports", "event_person", "ship_mission", "events_by_country",
    "ports_by_country", "country_of_port", "other",
]
MAX_LEN = 40
FILTERS = 128
EPOCHS = 5
BATCH = 32
LR = 2e-3          # 仅训练 TextCNN 头（BERT 冻结），可用较大学习率
SEED = 42
MODEL_NAME = os.getenv("BERT_MODEL_DIR", "bert-base-chinese")
FREEZE_BERT = True


def load_data(path):
    rows = []
    with open(path, encoding="utf8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                rows.append((row[0], row[1]))
    return rows


def encode_batch(texts, tokenizer):
    enc = tokenizer(
        texts, max_length=MAX_LEN, padding="max_length",
        truncation=True, return_tensors="pt",
    )
    return enc["input_ids"], enc["attention_mask"]


def main():
    setup_log("train_bert_intent")
    if not _HAS_TRANSFORMERS:
        print("[错误] 未安装 transformers。请先执行：pip install transformers")
        print("        并确保可获取中文 BERT 权重（bert-base-chinese），详见文件头注释。")
        return

    random.seed(SEED)
    torch.manual_seed(SEED)

    train_rows = load_data(os.path.join(BASE_DIR, "data", "intent", "train.csv"))
    test_rows = load_data(os.path.join(BASE_DIR, "data", "intent", "test.csv"))
    label2id = {l: i for i, l in enumerate(LABELS)}
    print("BERT 意图训练样本 %d 条，测试样本 %d 条" % (len(train_rows), len(test_rows)))

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    bert = BertModel.from_pretrained(MODEL_NAME)
    if FREEZE_BERT:
        for p in bert.parameters():
            p.requires_grad = False
    bert.eval()

    from models.bert_intent import BertTextCNN  # noqa: E402
    cnn = BertTextCNN(len(LABELS), filters=FILTERS)
    opt = optim.Adam(cnn.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    train_x = [q for q, _ in train_rows]
    train_y = torch.tensor([label2id[l] for _, l in train_rows], dtype=torch.long)

    for epoch in range(EPOCHS):
        cnn.train()
        idx = list(range(len(train_x)))
        random.shuffle(idx)
        total = correct = 0
        loss_sum = 0.0
        for i in range(0, len(idx), BATCH):
            b = idx[i:i + BATCH]
            input_ids, attention_mask = encode_batch([train_x[j] for j in b], tokenizer)
            yb = train_y[b]
            with torch.no_grad():
                outputs = bert(input_ids=input_ids, attention_mask=attention_mask)
                hidden = outputs.last_hidden_state
            opt.zero_grad()
            logits = cnn(hidden)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(b)
            correct += (logits.argmax(1) == yb).sum().item()
            total += len(b)
        print("epoch %02d/%d  train_acc=%.4f  loss=%.4f"
              % (epoch + 1, EPOCHS, correct / total, loss_sum / total))

    # 测试集评估
    cnn.eval()
    correct = total = 0
    with torch.no_grad():
        for i in range(0, len(test_rows), BATCH):
            b = test_rows[i:i + BATCH]
            input_ids, attention_mask = encode_batch([q for q, _ in b], tokenizer)
            yb = torch.tensor([label2id[l] for _, l in b], dtype=torch.long)
            outputs = bert(input_ids=input_ids, attention_mask=attention_mask)
            logits = cnn(outputs.last_hidden_state)
            correct += (logits.argmax(1) == yb).sum().item()
            total += len(b)
    print("TEST accuracy = %.4f" % (correct / total))

    os.makedirs(os.path.join(BASE_DIR, "checkpoints"), exist_ok=True)
    ckpt = {
        "cnn_state": cnn.state_dict(),
        "id2label": LABELS,
        "model_name": os.path.basename(MODEL_NAME.rstrip("/\\")),
        "max_len": MAX_LEN,
        "filters": FILTERS,
    }
    torch.save(ckpt, os.path.join(BASE_DIR, "checkpoints", "bert_intent.pt"))
    print("已保存 checkpoints/bert_intent.pt")


if __name__ == "__main__":
    main()
