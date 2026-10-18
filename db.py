# -*- coding: utf-8 -*-
"""Neo4j 连接工厂。

连接参数统一从环境变量读取，避免在代码中硬编码密码：

  NEO4J_URI      bolt 连接地址（默认 bolt://127.0.0.1:7687）
  NEO4J_USER     用户名（默认 neo4j）
  NEO4J_PASSWORD 密码（必填，公开仓库中不得硬编码）

示例（Windows PowerShell）：
  $env:NEO4J_PASSWORD = "你的密码"
示例（Git Bash）：
  export NEO4J_PASSWORD="你的密码"
"""
import os

from py2neo import Graph


def get_graph():
    return Graph(
        os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
