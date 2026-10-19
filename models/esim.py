# -*- coding: utf-8 -*-
"""PyTorch 版 ESIM 实体规范化。

ESIM（Enhanced Sequential Inference Model，增强型序列推理模型）架构：
  字符嵌入 → BiLSTM 编码 → 软注意力局部推理 → 组合 BiLSTM → 均值/最大池化
  → MLP → 2 分类（判断「片段 vs 候选实体」是否匹配）。

对外提供与字符 n-gram 版相同的接口：normalize(word, etype) -> 规范实体名。
"""
import os

import torch
import torch.nn as nn
import torch.nn.functional as F

PAD = 0
OOV = 1


class ESIM(nn.Module):
    """ESIM：编码 → 软注意力对齐 → 组合 → 池化 → MLP 二分类。"""

    def __init__(self, vocab_size, embed_dim, hidden_dim, num_classes=2, dropout=0.2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.encoder = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        # m = [编码(2H), 对齐(2H), 差(2H), 乘(2H)] = 8H
        self.composition = nn.LSTM(hidden_dim * 8, hidden_dim,
                                   batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim * 8, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def _encode(self, x):
        emb = self.embedding(x)
        out, _ = self.encoder(emb)  # (B, T, 2H)
        return out

    def _soft_align(self, a, b):
        # a: (B, Ta, D), b: (B, Tb, D)
        attn = torch.bmm(a, b.transpose(1, 2))                    # (B, Ta, Tb)
        align_a = torch.bmm(F.softmax(attn, dim=2), b)            # (B, Ta, D)
        align_b = torch.bmm(F.softmax(attn, dim=1).transpose(1, 2), a)  # (B, Tb, D)
        return align_a, align_b

    def forward(self, x1, x2):
        # x1 / x2: (B, T) 字符 id
        a = self._encode(x1)
        b = self._encode(x2)
        align_a, align_b = self._soft_align(a, b)
        m_a = torch.cat([a, align_a, a - align_a, a * align_a], dim=2)  # (B, Ta, 8H)
        m_b = torch.cat([b, align_b, b - align_b, b * align_b], dim=2)  # (B, Tb, 8H)
        comp_a, _ = self.composition(m_a)
        comp_b, _ = self.composition(m_b)
        avg_a = comp_a.mean(dim=1)
        max_a = comp_a.max(dim=1).values
        avg_b = comp_b.mean(dim=1)
        max_b = comp_b.max(dim=1).values
        v = torch.cat([avg_a, max_a, avg_b, max_b], dim=1)  # (B, 8H)
        v = self.dropout(v)
        return self.mlp(v)  # (B, num_classes)


class ESIMEntityMatcher(object):
    """加载 ESIM checkpoint，提供 normalize(word, etype)。"""

    def __init__(self, checkpoint_path=None, entity_lists=None):
        self.model = None
        self.word2id = None
        self.max_len = 20
        self.entity_lists = entity_lists or {}
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load(checkpoint_path)

    def load(self, path):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        self.word2id = ckpt["word2id"]
        self.max_len = ckpt.get("max_len", 20)
        self.model = ESIM(
            ckpt["vocab_size"],
            ckpt.get("embed_dim", 100),
            ckpt.get("hidden_dim", 128),
        )
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()

    def _encode(self, text):
        ids = [self.word2id.get(ch, OOV) for ch in text[:self.max_len]]
        ids = ids + [PAD] * (self.max_len - len(ids))
        return torch.tensor(ids, dtype=torch.long).unsqueeze(0)

    def match_score(self, mention, candidate):
        """返回「匹配类」的概率（0~1）。"""
        if self.model is None:
            return 0.0
        with torch.no_grad():
            logits = self.model(self._encode(mention), self._encode(candidate))
            probs = F.softmax(logits, dim=1)
            return float(probs[0, 1].item())

    def normalize(self, word, etype, threshold=0.5):
        candidates = self.entity_lists.get(etype, [])
        if not candidates:
            return word
        if word in candidates:
            return word

        # 1) 确定性子串匹配（词是候选的子串，或候选是词的子串）：
        #    闭域专名（港口/船只等）的模糊写法基本都是「去尾」子串，直接命中。
        subs = [c for c in candidates if word in c or c in word]
        if subs:
            return min(subs, key=lambda c: abs(len(c) - len(word)))

        # 2) 无子串关系时，才交给 ESIM 做语义匹配；但要求两者至少共享一个
        #    字符（专名不存在「零字符重叠的同义写法」，可挡住无把握的猜测）。
        shared = [c for c in candidates if set(word) & set(c)]
        if not shared or self.model is None:
            return word

        best = max(shared, key=lambda c: self.match_score(word, c))
        if self.match_score(word, best) >= threshold:
            return best
        return word
