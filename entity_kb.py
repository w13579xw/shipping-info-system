# -*- coding: utf-8 -*-
"""航运历史领域实体知识库（单一数据源）。

词典版（Named_Entity_Recognition.py）与深度学习流水线（nlp_pipeline.py）
共用本模块维护的实体表，避免多处重复维护。

实体来源：
  1. 原词典版实体表（历史事件/国家/任务/人物/港口/船只/年份）；
  2. graph_data/maritime_history.json（图谱真实节点名，如「中美贸易航线稳定」）。
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "graph_data", "maritime_history.json")

# 各类实体（航线/事件、国家、任务、人物、港口、船只、年份）
historical_events = [
    "中东航线贸易增长", "中国-欧洲货运航线", "中美贸易航线", "亚太地区航运整合",
    "亚洲-非洲货运航线", "亚洲东南部航线发展", "北极航道开通", "南极航道开发",
    "南美-非洲贸易航线", "印度洋航线发展", "印度洋航线建设", "美洲贸易航线扩张"
]

countries = [
    "中国", "俄罗斯", "加拿大", "南非", "卡塔尔", "印度", "埃及", "巴西", "德国",
    "新加坡", "日本", "智利", "比利时", "沙特阿拉伯", "泰国", "美国", "肯尼亚", "荷兰",
    "阿根廷", "阿联酋", "韩国", "马来西亚"
]

missions = [
    "国际贸易", "大宗商品运输", "油气运输", "海上航道开辟", "港口对接", "港口建设",
    "港口扩展", "物流管理", "环境保护", "航线建设", "航线扩展", "航运整合", "航道开发",
    "货物转运", "货物运输", "货运稳增长", "贸易增量", "跨洋运输", "跨洲际运输", "跨海港口运输", "运输管理"
]

persons = [
    "哈桑·阿里", "尼古拉·皮特罗夫", "张海涛", "拉斐尔·卡马奇", "李明", "李海华",
    "杰森·李", "王超", "田中哲也", "艾玛·罗莎", "萨尔曼·哈基姆"
]

ports = [
    "上海港", "东京港", "乌斯怀亚港", "亚历山大港", "内罗毕港", "吉达港", "吉隆坡港",
    "圣保罗港", "圣地亚哥港", "多哈港", "孟买港", "宁波舟山港", "安特卫普港",
    "布宜诺斯艾利斯港", "开普敦港", "德班港", "摩尔曼斯克港", "新加坡港", "曼谷港",
    "汉堡港", "洛杉矶港", "温哥华港", "纽约港", "蒙特利尔港", "迪拜港",
    "里约热内卢港", "釜山港", "阿拉斯加港", "鹿特丹港"
]

ships = [
    "东亚先锋号", "东南亚快线号", "东方之星号", "东方航运号", "亚洲海洋号",
    "北极先锋号", "南极探险号", "南美风帆号", "印度海之星号", "印度航运号",
    "新加坡之星号", "极地探险号", "极地航行号", "沙漠之舟号", "海洋之光号",
    "环太平洋号", "环球贸易号", "红海号", "美洲先锋号", "长赐号",
    "非洲之旅号", "非洲之星号"
]

years = [
    "2020", "2021", "2022", "2023", "2024", "2025"
]


def _load_json_event_names():
    """从图谱源数据读取历史事件节点名（如「中美贸易航线稳定」）。"""
    names = []
    try:
        with open(JSON_PATH, encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("event_name"):
                    names.append(data["event_name"])
    except Exception:
        pass
    return names


def _dedupe(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# 图谱真实事件节点名（含「中美贸易航线稳定」），供深度学习流水线使用
JSON_EVENT_NAMES = _load_json_event_names()

# 事件规范名 = 图谱节点名优先，再并入词典版别名（如「中美贸易航线」）
EVENTS = _dedupe(JSON_EVENT_NAMES + historical_events)
