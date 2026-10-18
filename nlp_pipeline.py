# -*- coding: utf-8 -*-
"""统一问答流水线：意图识别 → 命名实体识别 → 实体规范化 → Cypher → Neo4j。

深度学习模型缺失或运行出错时，回退到词典版
（Named_Entity_Recognition.process_question）作为兜底。
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from models.intent_textcnn import IntentClassifier  # noqa: E402
from models.ner_bilstm_crf import NERModel  # noqa: E402
from models.entity_normalizer import normalize  # noqa: E402

# 意图 -> 词典版 query_type
INTENT_TO_QUERY = {
    "event_ports": "ports",
    "event_person": "person",
    "ship_mission": "mission",
    "events_by_country": "event_by_country",
    "ports_by_country": "ports_by_country",
    "country_of_port": "country_by_ports",
    "other": "unknown",
}

# query_type -> 必需的实体槽位（缺失则回退词典版）
REQUIRED_ENTITY = {
    "ports": "航线",
    "person": "航线",
    "mission": "船只",
    "event_by_country": "国家",
    "ports_by_country": "国家",
    "country_by_ports": "港口",
}

# 实体类型 -> 词典版 entities 字典的键
ETYPE_TO_KEY = {
    "event": "航线",
    "country": "国家",
    "mission": "任务",
    "person": "负责人",
    "port": "港口",
    "ship": "船只",
    "year": "年份",
}

_intent_model = None
_ner_model = None


def _load_models():
    global _intent_model, _ner_model
    if _intent_model is None:
        _intent_model = IntentClassifier(os.path.join(BASE_DIR, "checkpoints", "intent.pt"))
    if _ner_model is None:
        _ner_model = NERModel(os.path.join(BASE_DIR, "checkpoints", "ner.pt"))
    return _intent_model, _ner_model


def answer(question):
    """对问题返回答案列表（与词典版 process_question 返回结构一致）。"""
    try:
        intent_model, ner_model = _load_models()
        if intent_model.model is None or ner_model.model is None:
            return _fallback(question)
    except Exception:
        return _fallback(question)

    try:
        intent, _conf = intent_model.predict(question)
        query_type = INTENT_TO_QUERY.get(intent, "unknown")

        entities = {"航线": None, "船只": None, "港口": None, "任务": None,
                    "年份": None, "负责人": None, "国家": None}
        for word, etype in ner_model.predict(question):
            key = ETYPE_TO_KEY.get(etype)
            if key and entities[key] is None:
                entities[key] = normalize(word, etype)

        required = REQUIRED_ENTITY.get(query_type)
        if required and entities.get(required) is None:
            return _fallback(question)

        from Named_Entity_Recognition import build_cypher_query, execute_cypher_query
        cypher = build_cypher_query(entities, query_type)
        output = [record[0] for record in execute_cypher_query(cypher)]
        return output
    except Exception:
        return _fallback(question)


def _fallback(question):
    try:
        from Named_Entity_Recognition import process_question
        return process_question(question)
    except Exception:
        return []


if __name__ == "__main__":
    # 便于本地直接调试（需 Neo4j 已启动并导入图谱）
    for q in [
        "上海港属于哪个国家？",
        "谁是亚太地区航运整合的负责人？",
        "长赐号的任务是什么？",
        "中国有哪些港口？",
    ]:
        print(q, "->", answer(q))
