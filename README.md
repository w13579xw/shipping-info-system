# 航运历史问答系统（V1.0）

一个基于 **Flask + Neo4j + 深度学习** 的航运文化历史问答系统。用户用自然语言提问（如「长赐号的任务是什么？」），系统经过意图识别、命名实体识别、实体规范化后生成 Cypher 查询，从 Neo4j 知识图谱中返回答案。

> 这是本项目的 **V1.0**（早期问答系统）。后续 V2.0 / V3.0 在其它分支上继续演进。

---

## 1. 系统流程

```
问题
  │
  ├─ 意图识别        TextCNN（7 类意图）
  ├─ 命名实体识别    BiLSTM-CRF（7 类实体，BIO 标注）
  ├─ 实体规范化      字符 n-gram 重叠度（闭域实体）
  ├─ 生成 Cypher     复用词典版 6 种查询模板
  └─ Neo4j 查询      返回答案列表
```

深度学习模型缺失或运行出错时，自动回退到**词典版**（`Named_Entity_Recognition.py`）作为兜底。

## 2. 目录结构

```
QA/
├─ app.py                      Flask 入口（/ask 接口）
├─ nlp_pipeline.py             统一问答流水线 answer(question)
├─ entity_kb.py                航运域实体知识库（单一数据源）
├─ db.py                       Neo4j 连接工厂（环境变量配置）
├─ Named_Entity_Recognition.py 词典版问答（兜底，含 6 种 Cypher 模板）
├─ build_kg_utils.py           知识图谱构建脚本
├─ prepare_data.py             训练数据合成脚本
├─ models/                     深度学习组件（PyTorch）
│   ├─ crf.py                  线性链 CRF
│   ├─ intent_textcnn.py       字符级 TextCNN 意图分类
│   ├─ ner_bilstm_crf.py       BiLSTM-CRF 命名实体识别
│   ├─ entity_normalizer.py    实体规范化
│   ├─ train_intent.py         意图分类训练脚本
│   └─ train_ner.py            NER 训练脚本
├─ checkpoints/                训练好的权重（intent.pt / ner.pt，各 <4MB）
├─ graph_data/                 图谱源数据（maritime_history.json 等）
├─ templates/                  前端页面
└─ legacy/                     旧版医疗域/新闻语料组件（不随仓库发布，见 §7）
```

## 3. 知识图谱 Schema

- **7 类实体**：历史事件、国家、年份、人物、任务、港口、船只
- **10 类关系**：`happened_in`、`occurred_in_year`、`involved_person`、`involved_mission`、`involved_port`、`operated_ship`、`located_in`、`belongs_to`、`carried_out_mission`、`connected_to`

## 4. 意图与实体

**7 类意图**（对应 6 种查询 + 兜底）：

| 意图 | 含义 | 示例 |
| --- | --- | --- |
| event_ports | 事件涉及哪些港口 | 中美贸易航线的主要港口有哪些？ |
| event_person | 事件的负责人 | 谁是亚太地区航运整合的负责人？ |
| ship_mission | 船只的任务 | 长赐号的任务是什么？ |
| events_by_country | 国家的历史事件 | 中国有哪些历史事件？ |
| ports_by_country | 国家的港口 | 中国有哪些港口？ |
| country_of_port | 港口属于哪个国家 | 东京港是哪个国家的？ |
| other | 无法回答 | 今天天气怎么样？ |

**7 类实体**（BIO 标注）：历史事件(event)、国家(country)、任务(mission)、人物(person)、港口(port)、船只(ship)、年份(year)。

## 5. 安装与运行

### 5.1 依赖

```bash
pip install -r requirements.txt
```

> 深度学习模型基于 **PyTorch（CPU 即可）**，无需 TensorFlow/keras。

### 5.2 Neo4j 与连接配置

1. 启动 Neo4j（默认 `bolt://127.0.0.1:7687`）。
2. 连接参数通过环境变量配置（**密码请勿硬编码**）：

   ```bash
   # Windows PowerShell
   $env:NEO4J_URI = "bolt://127.0.0.1:7687"
   $env:NEO4J_USER = "neo4j"
   $env:NEO4J_PASSWORD = "你的密码"

   # Git Bash / Linux / macOS
   export NEO4J_URI="bolt://127.0.0.1:7687"
   export NEO4J_USER="neo4j"
   export NEO4J_PASSWORD="你的密码"
   ```

3. 导入航运历史图谱：

   ```bash
   python build_kg_utils.py
   ```

### 5.3 启动服务

```bash
python app.py
```

浏览器访问 `http://127.0.0.1:5000/`，输入问题即可查询。

## 6. 数据合成与模型训练

训练数据由 `graph_data/maritime_history.json` + 实体表自动合成（约 550 条，按 8:2 划分）：

```bash
python prepare_data.py          # 生成 data/intent/* 与 data/ner/*
python models/train_intent.py   # 训练意图分类，产出 checkpoints/intent.pt
python models/train_ner.py      # 训练 NER，产出 checkpoints/ner.pt
```

在合成数据上：意图分类准确率 ≈ 100%，NER 实体 F1 ≈ 0.99（CPU 数分钟内完成）。仓库已附带训练好的 `checkpoints/*.pt`，可直接运行，无需重新训练。

## 7. 说明与限制

- **合成数据**：模型在模板化合成数据上训练，主要学会「模板问法」，对超纲措辞的泛化有限——因此**词典版保留为兜底**。
- **意图识别降级**：原「BERT+TextCNN 意图识别」依赖 bert4keras + TF1，且 BERT 权重缺失，本机无法复现；已用**从零训练的字符级 TextCNN** 替代（仍属深度学习，但不含预训练 BERT）。
- **实体规范化轻量化**：航运域实体为闭集（几十个），原医疗域 ESIM 语义匹配改为**字符 n-gram 重叠度**匹配。
- **旧版组件**：`legacy/` 目录保存早期从医疗 NLP 教程迁移的原型（医疗域 BERT 意图识别、医疗域 BiLSTM-CRF、医疗域 ESIM、新闻语料），与航运域无关，且包含 12MB 的 `.h5` 旧权重，**已通过 `.gitignore` 排除在版本库之外**。
