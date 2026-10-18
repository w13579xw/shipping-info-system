# -*- coding: utf-8 -*-
"""BERT + TextCNN 意图分类器（可选组件，依赖 transformers + 中文 BERT 权重）。

与字符级 TextCNN 版 IntentClassifier 提供相同接口：
    predict(text) -> (intent, confidence)
加载失败（缺 transformers 或缺权重）时 predict 返回 (None, 0.0)，由调用方回退。

用法：
    clf = BertIntentClassifier("checkpoints/bert_intent.pt")
    intent, conf = clf.predict("长赐号的任务是什么？")
"""
import os

import torch
import torch.nn as nn
import torch.nn.functional as F

# 7 类意图（与字符级 TextCNN 版一致）
LABELS = [
    "event_ports", "event_person", "ship_mission", "events_by_country",
    "ports_by_country", "country_of_port", "other",
]

try:
    from transformers import AutoTokenizer, BertModel
    _HAS_TRANSFORMERS = True
except Exception:  # pragma: no cover - 未安装 transformers 时优雅降级
    _HAS_TRANSFORMERS = False


class BertTextCNN(nn.Module):
    """接在 BERT 最后一层 hidden states 之上的 TextCNN 分类头。"""

    def __init__(self, num_classes, bert_dim=768, filters=128,
                 kernels=(3, 4, 5), dropout=0.3):
        super().__init__()
        self.convs = nn.ModuleList([
            nn.Conv1d(bert_dim, filters, k, padding="same") for k in kernels
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(filters * len(kernels), num_classes)

    def forward(self, bert_output):
        # bert_output: (B, T, bert_dim)，BERT 最后一层 hidden states
        x = bert_output.transpose(1, 2)                      # (B, bert_dim, T)
        pooled = [F.relu(conv(x)).max(dim=2).values for conv in self.convs]
        feat = torch.cat(pooled, dim=1)                      # (B, filters*len(kernels))
        feat = self.dropout(feat)
        return self.fc(feat)                                 # (B, num_classes)


class BertIntentClassifier(object):
    """加载 BERT+TextCNN checkpoint，提供 predict(text) -> (intent, confidence)。"""

    def __init__(self, checkpoint_path=None, model_name="bert-base-chinese"):
        self.model = None
        self.cnn = None
        self.tokenizer = None
        self.id2label = LABELS
        self.max_len = 40
        self.model_name = model_name
        if checkpoint_path and os.path.exists(checkpoint_path) and _HAS_TRANSFORMERS:
            try:
                self.load(checkpoint_path, model_name)
            except Exception:
                # 权重缺失 / 加载失败时保持 model=None，由调用方回退
                self.model = None

    def load(self, path, model_name="bert-base-chinese"):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        self.model_name = ckpt.get("model_name", model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = BertModel.from_pretrained(self.model_name)
        self.id2label = ckpt.get("id2label", LABELS)
        self.max_len = ckpt.get("max_len", 40)
        self.cnn = BertTextCNN(len(self.id2label), filters=ckpt.get("filters", 128))
        self.cnn.load_state_dict(ckpt["cnn_state"])
        self.model.eval()
        self.cnn.eval()

    def _encode(self, text):
        enc = self.tokenizer(
            text, max_length=self.max_len, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        return enc["input_ids"], enc["attention_mask"]

    def predict(self, text):
        if self.model is None or self.cnn is None:
            return None, 0.0
        with torch.no_grad():
            input_ids, attention_mask = self._encode(text)
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = self.cnn(outputs.last_hidden_state)
            probs = F.softmax(logits, dim=1)
            idx = probs.argmax(dim=1).item()
            return self.id2label[idx], float(probs[0, idx].item())
