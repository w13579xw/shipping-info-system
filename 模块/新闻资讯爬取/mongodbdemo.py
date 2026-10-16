#!/usr/bin/env python
# -*- coding:utf-8 -*-


from pymongo import MongoClient

# 配置MongoDB连接
client = MongoClient('mongodb://localhost:27017/')  # 连接到本地MongoDB实例
db = client['news_db']  # 使用或创建一个名为news_db的数据库
collection = db['news_collection']  # 使用或创建一个集合（表）来保存新闻

# 查询所有文档并按日期降序排序
all_news = collection.find().sort("date", -1)[:30]

for news in all_news:
    print(f"Title: {news['title']}")
    print(f"Date: {news['date']}")
    print(f"Body: {news['body']}")
    print(f"Keywords: {news['keywords']}")
    print("-" * 50)