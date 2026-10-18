# -*- coding: utf-8 -*-
"""训练 BiLSTM-CRF 命名实体识别，产出 checkpoints/ner.pt。"""
import os
import random
import sys

import torch
import torch.optim as optim

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from models.ner_bilstm_crf import BiLSTMCRF, PAD, OOV  # noqa: E402

ENTITY_TYPES = ["event", "country", "mission", "person", "port", "ship", "year"]
MAX_LEN = 40
EMBED_DIM = 100
HIDDEN_DIM = 256
EPOCHS = 80
BATCH = 64
LR = 1e-3
SEED = 42


def load_bio(path):
    sentences = []
    chars = []
    tags = []
    with open(path, encoding="utf8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                if chars:
                    sentences.append(("".join(chars), tags))
                    chars = []
                    tags = []
                continue
            parts = line.split()
            if len(parts) >= 2:
                chars.append(parts[0])
                tags.append(parts[1])
        if chars:
            sentences.append(("".join(chars), tags))
    return sentences


def build_vocab(sentences):
    chars = set()
    for s, _ in sentences:
        chars.update(s)
    word2id = {"<pad>": PAD, "<oov>": OOV}
    for i, ch in enumerate(sorted(chars)):
        word2id[ch] = i + 2
    return word2id


def build_tag_maps():
    ordered = ["O"]
    for t in ENTITY_TYPES:
        ordered += ["B_" + t, "I_" + t]
    tag2id = {t: i + 1 for i, t in enumerate(ordered)}
    id2tag = {i + 1: t for i, t in enumerate(ordered)}
    id2tag[0] = "padding"
    return tag2id, id2tag


def encode(sentence, tags, word2id, tag2id):
    ids = [word2id.get(ch, OOV) for ch in sentence[:MAX_LEN]]
    tids = [tag2id[t] for t in tags[:MAX_LEN]]
    length = len(ids)
    mask = [1] * length + [0] * (MAX_LEN - length)
    ids += [PAD] * (MAX_LEN - length)
    tids += [0] * (MAX_LEN - length)
    return ids, tids, mask, length


def spans_from_tags(tags, id2tag, length):
    result = set()
    start = None
    etype = None
    for i in range(length):
        tag = id2tag[tags[i]]
        if tag.startswith("B_"):
            if start is not None:
                result.add((start, i, etype))
            start = i
            etype = tag[2:]
        elif tag.startswith("I_") and start is not None and etype == tag[2:]:
            continue
        else:
            if start is not None:
                result.add((start, i, etype))
            start = None
            etype = None
    if start is not None:
        result.add((start, length, etype))
    return result


def evaluate(model, data, word2id, tag2id, id2tag):
    model.eval()
    tp = fp = fn = 0
    with torch.no_grad():
        for sentence, tags in data:
            ids, _, mask, length = encode(sentence, tags, word2id, tag2id)
            x = torch.tensor(ids, dtype=torch.long).unsqueeze(0)
            m = torch.tensor(mask, dtype=torch.float).unsqueeze(0)
            emissions = model(x, m)
            path = model.decode(emissions, [length])[0]
            gold = spans_from_tags([tag2id[t] for t in tags[:length]], id2tag, length)
            pred = spans_from_tags(path, id2tag, length)
            tp += len(gold & pred)
            fp += len(pred - gold)
            fn += len(gold - pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)

    train_data = load_bio(os.path.join(BASE_DIR, "data", "ner", "train.txt"))
    test_data = load_bio(os.path.join(BASE_DIR, "data", "ner", "test.txt"))
    word2id = build_vocab(train_data + test_data)
    tag2id, id2tag = build_tag_maps()
    num_tags = len(ENTITY_TYPES) * 2 + 1  # O + B_/I_ * 7

    model = BiLSTMCRF(len(word2id), EMBED_DIM, HIDDEN_DIM, num_tags)
    opt = optim.Adam(model.parameters(), lr=LR)

    # 预编码
    train_enc = [encode(s, t, word2id, tag2id) for s, t in train_data]
    train_x = torch.tensor([e[0] for e in train_enc], dtype=torch.long)
    train_tags = torch.tensor([e[1] for e in train_enc], dtype=torch.long)
    train_mask = torch.tensor([e[2] for e in train_enc], dtype=torch.float)

    for epoch in range(EPOCHS):
        model.train()
        idx = list(range(len(train_x)))
        random.shuffle(idx)
        loss_sum = 0.0
        total = 0
        for i in range(0, len(idx), BATCH):
            b = idx[i:i + BATCH]
            xb = train_x[b]
            mb = train_mask[b]
            tb = train_tags[b]
            opt.zero_grad()
            loss = model.neg_log_likelihood(xb, mb, tb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            loss_sum += loss.item() * len(b)
            total += len(b)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print("epoch %02d/%d  loss=%.4f" % (epoch + 1, EPOCHS, loss_sum / total))

    p, r, f1 = evaluate(model, test_data, word2id, tag2id, id2tag)
    print("TEST precision=%.4f  recall=%.4f  f1=%.4f" % (p, r, f1))

    os.makedirs(os.path.join(BASE_DIR, "checkpoints"), exist_ok=True)
    ckpt = {
        "model_state": model.state_dict(),
        "word2id": word2id,
        "id2tag": id2tag,
        "max_len": MAX_LEN,
        "vocab_size": len(word2id),
        "num_tags": num_tags,
        "embed_dim": EMBED_DIM,
        "hidden_dim": HIDDEN_DIM,
    }
    torch.save(ckpt, os.path.join(BASE_DIR, "checkpoints", "ner.pt"))
    print("已保存 checkpoints/ner.pt")


if __name__ == "__main__":
    main()
