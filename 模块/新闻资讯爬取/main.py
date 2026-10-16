#!/usr/bin/env python
# -*- coding:utf-8 -*-


from pymongo import MongoClient
from utils import bm25


# 连接到MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['news_db']
collection = db['news_collection']

# 从MongoDB检索文档
documents = list(collection.find())

# 将文档内容转换为字符串列表
corpus = [doc['title'] + ' ' + doc['body'] for doc in documents]

# 使用BM25搜索
results = bm25.bm25_search(corpus, "马士基，船员", language='chinese')

# 打印搜索结果
for doc_id, score, doc_content in results:
    print(f"文档ID: {doc_id}, 得分: {score}, 内容: {doc_content}")