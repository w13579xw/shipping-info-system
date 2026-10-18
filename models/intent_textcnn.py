# -*- coding: utf-8 -*-
"""字符级 TextCNN 意图分类器（从零训练，替代原医疗域 BERT+TextCNN）。

原组件依赖 bert4keras + TF1，且 BERT 权重缺失，无法在本机复现；本实现用
PyTorch 字符级 TextCNN 从合成数据训练，模型体积小、CPU 即可推理。
"""
import os

import torch
import torch.nn as nn
import torch.nn.functional as F

PAD = 0
OOV = 1


class TextCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_classes,
                 kernels=(3, 4, 5), filters=128, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, filters, k, padding="same") for k in kernels
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(filters * len(kernels), num_classes)

    def forward(self, x):
        # x: (B, T) long
        emb = self.embedding(x).transpose(1, 2)          # (B, E, T)
        pooled = [F.relu(conv(emb)).max(dim=2).values for conv in self.convs]
        feat = torch.cat(pooled, dim=1)                  # (B, filters*len(kernels))
        feat = self.dropout(feat)
        return self.fc(feat)                             # (B, num_classes)


class IntentClassifier(object):
    """加载 checkpoint 并提供 predict(text) -> (intent, confidence)。"""

    def __init__(self, checkpoint_path=None):
        self.model = None
        self.word2id = None
        self.id2label = None
        self.max_len = 40
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load(checkpoint_path)

    def load(self, path):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        self.word2id = ckpt["word2id"]
        self.id2label = ckpt["id2label"]
        self.max_len = ckpt["max_len"]
        self.model = TextCNN(
            ckpt["vocab_size"],
            ckpt.get("embed_dim", 100),
            len(self.id2label),
            filters=ckpt.get("filters", 128),
        )
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()

    def _encode(self, text):
        ids = [self.word2id.get(ch, OOV) for ch in text[:self.max_len]]
        ids = ids + [PAD] * (self.max_len - len(ids))
        return torch.tensor(ids, dtype=torch.long).unsqueeze(0)

    def predict(self, text):
        if self.model is None:
            return None, 0.0
        with torch.no_grad():
            logits = self.model(self._encode(text))
            probs = F.softmax(logits, dim=1)
            idx = probs.argmax(dim=1).item()
            return self.id2label[idx], float(probs[0, idx].item())
