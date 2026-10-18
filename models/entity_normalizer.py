# -*- coding: utf-8 -*-
"""轻量实体规范化（替代原医疗域 ESIM 语义匹配）。

航运域实体为闭集（几十个），无需 ESIM 级别的语义模型。这里用字符 n-gram
重叠度 + 子串匹配，把 NER 识别出的实体片段映射到规范实体表。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import entity_kb  # noqa: E402

ENTITY_LISTS = {
    "event": entity_kb.EVENTS,
    "country": entity_kb.countries,
    "mission": entity_kb.missions,
    "person": entity_kb.persons,
    "port": entity_kb.ports,
    "ship": entity_kb.ships,
    "year": entity_kb.years,
}


def _ngrams(s, n=2):
    if len(s) < n:
        return [s]
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def _overlap(a, b, n=2):
    ga, gb = set(_ngrams(a, n)), set(_ngrams(b, n))
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def normalize(word, etype, threshold=0.5):
    """把识别出的实体片段映射为规范实体名；无把握时原样返回。"""
    candidates = ENTITY_LISTS.get(etype, [])
    if not candidates:
        return word
    if word in candidates:
        return word
    best = None
    best_score = 0.0
    for cand in candidates:
        if word in cand or cand in word:
            score = 0.9 * min(len(word), len(cand)) / max(len(word), len(cand))
        else:
            score = _overlap(word, cand)
        if score > best_score:
            best_score = score
            best = cand
    if best is not None and best_score >= threshold:
        return best
    return word
