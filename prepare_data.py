# -*- coding: utf-8 -*-
"""从实体表 + maritime_history.json 自动合成航运域训练数据。

产出：
  data/intent/train.csv / test.csv   格式「问题,意图」（7 类意图）
  data/ner/train.txt  / test.txt     BIO 格式（每行「字 标签」，空行分隔句子）
"""
import csv
import os
import random

import entity_kb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENT_DIR = os.path.join(BASE_DIR, "data", "intent")
NER_DIR = os.path.join(BASE_DIR, "data", "ner")

SEED = 42
TRAIN_RATIO = 0.8

# 意图 -> 问句模板（{e} 事件 / {s} 船只 / {c} 国家 / {p} 港口）
INTENT_TEMPLATES = {
    "event_ports": [
        "{e}涉及哪些港口？", "{e}的主要港口有哪些？",
        "{e}途经哪些港口？", "{e}的港口有哪些？",
    ],
    "event_person": [
        "谁是{e}的负责人？", "{e}的负责人是谁？", "{e}由谁负责？",
    ],
    "ship_mission": [
        "{s}的任务是什么？", "{s}执行什么任务？", "{s}承担什么任务？",
        "{s}承担了什么任务？", "{s}负责什么任务？", "{s}主要从事什么？",
    ],
    "events_by_country": [
        "{c}有哪些历史事件？", "{c}的历史事件有哪些？", "{c}发生过哪些航运事件？",
    ],
    "ports_by_country": [
        "{c}有哪些港口？", "{c}的港口有哪些？",
    ],
    "country_of_port": [
        "{p}属于哪个国家？", "{p}是哪个国家的？", "{p}在哪个国家？",
    ],
}

# 每种意图对应的目标实体（实体类型、实体列表、模板占位符）
ENTITY_BY_INTENT = {
    "event_ports": ("event", "EVENTS", "e"),
    "event_person": ("event", "EVENTS", "e"),
    "ship_mission": ("ship", "ships", "s"),
    "events_by_country": ("country", "countries", "c"),
    "ports_by_country": ("country", "countries", "c"),
    "country_of_port": ("port", "ports", "p"),
}

OTHER_QUESTIONS = [
    "今天天气怎么样？", "你好", "你是谁？", "介绍一下航运系统", "什么是航运？",
    "帮我订一张船票", "明天有什么新闻？", "谢谢", "请问有什么可以帮你？",
    "海运和空运哪个便宜？", "如何成为一名船长？", "再见",
]


def _make_samples():
    samples = []  # [{"question": str, "intent": str, "ents": [(word, type), ...]}]
    for intent, templates in INTENT_TEMPLATES.items():
        etype, list_attr, key = ENTITY_BY_INTENT[intent]
        values = getattr(entity_kb, list_attr)
        for value in values:
            for tpl in templates:
                question = tpl.replace("{%s}" % key, value)
                samples.append({"question": question, "intent": intent,
                                "ents": [(value, etype)]})

    # other：通用噪声样本
    for q in OTHER_QUESTIONS:
        samples.append({"question": q, "intent": "other", "ents": []})

    # 补充 year / person / mission 样本，给对应 NER 标签提供训练信号
    for y in entity_kb.years:
        for tpl in ["{y}年有哪些航运事件？", "{y}年发生了什么？", "{y}年的航运情况如何？"]:
            samples.append({"question": tpl.replace("{y}", y),
                            "intent": "other", "ents": [(y, "year")]})
    for p in entity_kb.persons:
        for tpl in ["{p}是谁？", "{p}来自哪里？", "请问{p}是谁？"]:
            samples.append({"question": tpl.replace("{p}", p),
                            "intent": "other", "ents": [(p, "person")]})
    for m in entity_kb.missions:
        for tpl in ["{m}是什么意思？", "{m}指什么？", "什么是{m}？"]:
            samples.append({"question": tpl.replace("{m}", m),
                            "intent": "other", "ents": [(m, "mission")]})
    return samples


def _bio_tag(question, ents):
    tags = ["O"] * len(question)
    for word, etype in ents:
        start = question.find(word)
        if start == -1:
            continue
        for i in range(len(word)):
            tags[start + i] = ("B_" if i == 0 else "I_") + etype
    return tags


def _write_bio(path, samples):
    with open(path, "w", encoding="utf8") as f:
        for sample in samples:
            question = sample["question"]
            tags = _bio_tag(question, sample["ents"])
            for ch, tag in zip(question, tags):
                f.write("%s %s\n" % (ch, tag))
            f.write("\n")


def main():
    random.seed(SEED)
    samples = _make_samples()
    random.shuffle(samples)

    split = int(len(samples) * TRAIN_RATIO)
    train, test = samples[:split], samples[split:]

    os.makedirs(INTENT_DIR, exist_ok=True)
    os.makedirs(NER_DIR, exist_ok=True)

    for name, subset in [("train", train), ("test", test)]:
        with open(os.path.join(INTENT_DIR, name + ".csv"), "w", encoding="utf8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["question", "intent"])
            for s in subset:
                writer.writerow([s["question"], s["intent"]])
        _write_bio(os.path.join(NER_DIR, name + ".txt"), subset)

    # 统计各类意图数量
    from collections import Counter
    counter = Counter(s["intent"] for s in train)
    print("共生成样本 %d 条（train=%d / test=%d）" % (len(samples), len(train), len(test)))
    for intent in sorted(counter):
        print("  %-18s %d" % (intent, counter[intent]))
    print("已写入 data/intent/* 与 data/ner/*")


if __name__ == "__main__":
    main()
