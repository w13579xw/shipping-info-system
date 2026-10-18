# -*- coding: utf-8 -*-
"""PyTorch BiLSTM-CRF 命名实体识别（替代原 keras 医疗域 BiLSTM-CRF）。

BIO 标注，7 类实体：event / country / mission / person / port / ship / year。
"""
import os

import torch
import torch.nn as nn

from .crf import CRF

PAD = 0
OOV = 1


class BiLSTMCRF(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_tags, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers=1,
                            batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.hidden2tag = nn.Linear(hidden_dim * 2, num_tags + 2)
        self.crf = CRF(num_tags)
        self.num_tags = num_tags

    def forward(self, x, mask):
        # x: (B, T) long，mask: (B, T) float 0/1
        emb = self.embedding(x)
        lstm_out, _ = self.lstm(emb)
        lstm_out = self.dropout(lstm_out)
        return self.hidden2tag(lstm_out)  # (B, T, num_tags+2)

    def neg_log_likelihood(self, x, mask, tags):
        emissions = self.forward(x, mask)
        return self.crf(emissions, tags, mask)

    def decode(self, emissions, seq_lens):
        # emissions: (B, T, K)，seq_lens: 每个样本真实长度
        paths = []
        for i, length in enumerate(seq_lens):
            paths.append(self.crf.viterbi_decode(emissions[i, :length, :]))
        return paths


class NERModel(object):
    """加载 checkpoint 并提供 predict(text) -> [(词, 实体类型), ...]。"""

    def __init__(self, checkpoint_path=None):
        self.model = None
        self.word2id = None
        self.id2tag = None
        self.max_len = 40
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load(checkpoint_path)

    def load(self, path):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        self.word2id = ckpt["word2id"]
        self.id2tag = ckpt["id2tag"]
        self.max_len = ckpt["max_len"]
        self.model = BiLSTMCRF(
            ckpt["vocab_size"],
            ckpt.get("embed_dim", 100),
            ckpt.get("hidden_dim", 128),
            ckpt["num_tags"],
        )
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()

    def predict(self, text):
        if self.model is None:
            return []
        chars = list(text)[:self.max_len]
        length = len(chars)
        ids = [self.word2id.get(ch, OOV) for ch in chars]
        ids = ids + [PAD] * (self.max_len - length)
        x = torch.tensor(ids, dtype=torch.long).unsqueeze(0)
        mask = torch.zeros(1, self.max_len)
        mask[0, :length] = 1.0
        with torch.no_grad():
            emissions = self.model(x, mask)
            path = self.model.decode(emissions, [length])[0]
        return self._tags_to_entities(chars, path)

    def _tags_to_entities(self, chars, tags):
        entities = []
        cur = []
        cur_type = None
        for ch, t in zip(chars, tags):
            tag = self.id2tag.get(t, "O")
            if tag.startswith("B_"):
                if cur:
                    entities.append(("".join(cur), cur_type))
                cur = [ch]
                cur_type = tag[2:]
            elif tag.startswith("I_") and cur and cur_type == tag[2:]:
                cur.append(ch)
            else:
                if cur:
                    entities.append(("".join(cur), cur_type))
                cur = []
                cur_type = None
        if cur:
            entities.append(("".join(cur), cur_type))
        return entities
