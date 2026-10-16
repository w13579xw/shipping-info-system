#encoding:utf8
import os
import re
import json
import codecs
import threading
from py2neo import Graph
import pandas as pd
import numpy as np
from tqdm import tqdm
from myProject.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class PortKnowledgeGraphBuilder(object):
    def __init__(self):
        super(PortKnowledgeGraphBuilder, self).__init__()
        self.graph = Graph(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        # 定义实体节点
        self.countries = []
        self.cities = []
        self.ports = []
        self.regions = []
        self.routes = []

        # 构建实体关系
        self.rels_city_country = []
        self.rels_port_city = []
        self.rels_port_region = []
        self.rels_port_route = []

    def extract_triples(self, data_path):
        print("从json文件中转换抽取三元组")
        with open(data_path, 'r', encoding='utf8') as f:
            data = json.load(f)
            for record in tqdm(data, ncols=80):
                port = record.get('港口中文')
                city = record.get('城市中文')
                country = record.get('国家中文')
                region = record.get('地区')
                route = record.get('航线中文')

                # 过滤掉包含空值的记录
                if not any([port, city, country, region, route]):
                    continue

                if port: self.ports.append(port)
                if city: self.cities.append(city)
                if country: self.countries.append(country)
                if region: self.regions.append(region)
                if route: self.routes.append(route)

                # 提取关系，确保两端都不为空
                if city and country:
                    self.rels_city_country.append([city, 'belongs_to', country])
                if port and city:
                    self.rels_port_city.append([port, 'located_in', city])
                if port and region:
                    self.rels_port_region.append([port, 'in_region', region])
                if port and route:
                    self.rels_port_route.append([port, 'on_route', route])

    def write_nodes(self, entities, entity_type):
        print("写入 {0} 实体".format(entity_type))
        for node in tqdm(set(entities), ncols=80):
            if node:  # 忽略空值
                cql = """MERGE(n:{label}{{name:'{entity_name}'}})""".format(
                    label=entity_type, entity_name=node.replace("'", ""))
                try:
                    self.graph.run(cql)
                except Exception as e:
                    print(e)
                    print(cql)

    def write_edges(self, triples, head_type, tail_type):
        if not triples:
            return
        print("写入 {0} 关系".format(triples[0][1]))
        for head, relation, tail in tqdm(triples, ncols=80):
            if head and tail:  # 忽略两端为空的关系
                cql = """MATCH(p:{head_type}),(q:{tail_type})
                        WHERE p.name='{head}' AND q.name='{tail}'
                        MERGE (p)-[r:{relation}]->(q)""".format(
                    head_type=head_type, tail_type=tail_type, head=head.replace("'", ""),
                    tail=tail.replace("'", ""), relation=relation)
                try:
                    self.graph.run(cql)
                except Exception as e:
                    print(e)
                    print(cql)

    def create_entities(self):
        self.write_nodes(self.countries, '国家')
        self.write_nodes(self.cities, '城市')
        self.write_nodes(self.ports, '港口')
        self.write_nodes(self.regions, '地区')
        self.write_nodes(self.routes, '航线')

    def create_relations(self):
        self.write_edges(self.rels_city_country, '城市', '国家')
        self.write_edges(self.rels_port_city, '港口', '城市')
        self.write_edges(self.rels_port_region, '港口', '地区')
        self.write_edges(self.rels_port_route, '港口', '航线')


if __name__ == '__main__':
    path = "./port_data.json"
    builder = PortKnowledgeGraphBuilder()
    builder.extract_triples(path)
    builder.create_entities()
    builder.create_relations()