# -*- coding: utf-8 -*-
"""模块级测试脚本：分别评估各模块（不含系统联调）。

  - 意图识别（字符级 TextCNN）：准确率 + 各类别精确率/召回率/F1
  - 命名实体识别（BiLSTM-CRF）：实体级精确率/召回率/F1 + 各实体类型分解
  - 实体规范化（字符 n-gram）：确定性规则单元测试
  - 实体规范化（ESIM）：匹配准确率（训练型，语义匹配）
  - 意图识别（BERT+TextCNN，可选）：准确率（需 transformers + 中文 BERT 权重）

测试结果同时备份到 logs/evaluate_*.log。

用法：
  python evaluate.py
"""
import csv
import os
import sys
from collections import Counter, defaultdict

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from log_utils import setup_log  # noqa: E402
from models.intent_textcnn import IntentClassifier  # noqa: E402
from models.ner_bilstm_crf import BiLSTMCRF, NERModel  # noqa: E402
from models.entity_normalizer import normalize  # noqa: E402
from models.train_ner import load_bio, build_tag_maps, encode, spans_from_tags  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CKPT_INTENT = os.path.join(BASE, "checkpoints", "intent.pt")
CKPT_NER = os.path.join(BASE, "checkpoints", "ner.pt")


def load_intent_test():
    rows = []
    with open(os.path.join(BASE, "data", "intent", "test.csv"), encoding="utf8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                rows.append((row[0], row[1]))
    return rows


def eval_intent():
    print("=" * 60)
    print("【1】意图识别模块（字符级 TextCNN）")
    print("=" * 60)
    clf = IntentClassifier(CKPT_INTENT)
    if clf.model is None:
        print("  [跳过] 未找到 %s，请先运行 models/train_intent.py" % CKPT_INTENT)
        return
    rows = load_intent_test()
    labels = clf.id2label
    cm = defaultdict(lambda: defaultdict(int))
    correct = 0
    for q, gold in rows:
        pred, _ = clf.predict(q)
        cm[gold][pred] += 1
        if pred == gold:
            correct += 1
    acc = correct / len(rows)
    print("  测试集准确率 accuracy = %.4f  (%d/%d)" % (acc, correct, len(rows)))
    print("  各类别指标：")
    print("    %-18s %8s %8s %8s %6s" % ("类别", "精确率", "召回率", "F1", "样本数"))
    for label in labels:
        tp = cm[label][label]
        fp = sum(cm[g][label] for g in labels if g != label)
        fn = sum(cm[label][p] for p in labels if p != label)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        print("    %-18s %8.4f %8.4f %8.4f %6d" % (label, p, r, f1, sum(cm[label].values())))


def eval_ner():
    print()
    print("=" * 60)
    print("【2】命名实体识别模块（BiLSTM-CRF）")
    print("=" * 60)
    if not os.path.exists(CKPT_NER):
        print("  [跳过] 未找到 %s，请先运行 models/train_ner.py" % CKPT_NER)
        return
    ckpt = torch.load(CKPT_NER, map_location="cpu", weights_only=False)
    word2id = ckpt["word2id"]
    id2tag = ckpt["id2tag"]
    num_tags = ckpt["num_tags"]
    model = BiLSTMCRF(ckpt["vocab_size"], ckpt.get("embed_dim", 100),
                      ckpt.get("hidden_dim", 128), num_tags)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    tag2id = build_tag_maps()[0]

    test_data = load_bio(os.path.join(BASE, "data", "ner", "test.txt"))
    n_gold = Counter()
    n_pred = Counter()
    n_tp = Counter()
    with torch.no_grad():
        for sent, tags in test_data:
            ids, _, mask, length = encode(sent, tags, word2id, tag2id)
            x = torch.tensor(ids, dtype=torch.long).unsqueeze(0)
            m = torch.tensor(mask, dtype=torch.float).unsqueeze(0)
            emissions = model(x, m)
            path = model.decode(emissions, [length])[0]
            gold = spans_from_tags([tag2id[t] for t in tags[:length]], id2tag, length)
            pred = spans_from_tags(path, id2tag, length)
            for g in gold:
                n_gold[g[2]] += 1
            for p in pred:
                n_pred[p[2]] += 1
            for p in pred & gold:
                n_tp[p[2]] += 1

    tp = sum(n_tp.values())
    fp = sum(n_pred.values()) - tp
    fn = sum(n_gold.values()) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print("  实体级（整体）precision = %.4f  recall = %.4f  f1 = %.4f" % (precision, recall, f1))
    print("  各实体类型分解：")
    print("    %-10s %6s %6s %6s %8s %8s %8s" % ("类型", "gold", "pred", "tp", "精确率", "召回率", "F1"))
    for etype in sorted(set(list(n_gold) + list(n_pred))):
        g = n_gold[etype]
        p = n_pred[etype]
        t = n_tp[etype]
        ep = t / p if p else 0.0
        er = t / g if g else 0.0
        ef1 = 2 * ep * er / (ep + er) if ep + er else 0.0
        print("    %-10s %6d %6d %6d %8.4f %8.4f %8.4f" % (etype, g, p, t, ep, er, ef1))


def eval_normalizer():
    print()
    print("=" * 60)
    print("【3】实体规范化模块（字符 n-gram 重叠度）")
    print("=" * 60)
    print("  说明：确定性规则匹配（非训练型），以下为单元测试用例。")
    cases = [
        ("上海港", "port", "上海港"),
        ("亚太地区航运整合", "event", "亚太地区航运整合"),
        ("中美贸易航线", "event", "中美贸易航线"),
        ("鹿特丹", "port", "鹿特丹港"),
        ("长赐", "ship", "长赐号"),
        ("不存在的实体XYZ", "port", "不存在的实体XYZ"),
    ]
    passed = 0
    print("    %-20s %-8s %-20s %-20s %s" % ("输入片段", "类型", "输出", "期望", "结果"))
    for word, etype, expected in cases:
        got = normalize(word, etype)
        ok = (got == expected)
        passed += ok
        print("    %-20s %-8s %-20s %-20s %s" % (word, etype, got, expected, "通过" if ok else "失败"))
    print("  单元测试通过 %d/%d" % (passed, len(cases)))


def eval_esim():
    print()
    print("=" * 60)
    print("【4】实体规范化模块（ESIM 语义匹配）")
    print("=" * 60)
    ckpt_path = os.path.join(BASE, "checkpoints", "esim.pt")
    if not os.path.exists(ckpt_path):
        print("  [跳过] 未找到 %s，请先运行 models/train_esim.py" % ckpt_path)
        return
    from models.esim import ESIM  # noqa: E402
    from models.train_esim import load_pairs, accuracy  # noqa: E402
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model = ESIM(ckpt["vocab_size"], ckpt.get("embed_dim", 100),
                 ckpt.get("hidden_dim", 128))
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    test_pairs = load_pairs(os.path.join(BASE, "data", "esim", "test.csv"))
    acc = accuracy(model, test_pairs, ckpt["word2id"])
    print("  匹配准确率 accuracy = %.4f  (%d 条测试)" % (acc, len(test_pairs)))


def eval_bert_intent():
    print()
    print("=" * 60)
    print("【5】意图识别模块（BERT + TextCNN，可选）")
    print("=" * 60)
    ckpt_path = os.path.join(BASE, "checkpoints", "bert_intent.pt")
    try:
        from models.bert_intent import BertIntentClassifier  # noqa: E402
    except Exception:
        print("  [跳过] 未安装 transformers，无法加载 BERT 模型。")
        print("         安装：pip install transformers，并准备中文 BERT 权重（见 models/train_bert_intent.py）")
        return
    if not os.path.exists(ckpt_path):
        print("  [跳过] 未找到 %s，请先运行 models/train_bert_intent.py" % ckpt_path)
        return
    clf = BertIntentClassifier(ckpt_path)
    if clf.model is None:
        print("  [跳过] BERT 权重缺失或 transformers 未安装，无法评估。")
        return
    rows = load_intent_test()
    correct = 0
    for q, gold in rows:
        pred, _ = clf.predict(q)
        if pred == gold:
            correct += 1
    print("  测试集准确率 accuracy = %.4f  (%d/%d)" % (correct / len(rows), correct, len(rows)))


if __name__ == "__main__":
    setup_log("evaluate")
    eval_intent()
    eval_ner()
    eval_normalizer()
    eval_esim()
    eval_bert_intent()
