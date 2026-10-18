#encoding:utf8
import os
import re
import json
import codecs
import threading
from db import get_graph
import pandas as pd
import numpy as np
from tqdm import tqdm

class MaritimeHistoryExtractor(object):
    def __init__(self):
        super(MaritimeHistoryExtractor, self).__init__()
        # Neo4j 连接参数通过环境变量配置（见 db.py）
        self.graph = get_graph()

        # 定义航运文化历史的实体节点
        self.countries = []  # 国家
        self.historical_events = []  # 历史事件
        self.years = []  # 年份
        self.persons = []  # 人物
        self.missions = []  # 任务
        self.ports = []  # 港口
        self.ships = []  # 船只

        # 构建实体关系
        self.rels_event_country = []  # 历史事件-国家关系
        self.rels_event_year = []  # 历史事件-年份关系
        self.rels_event_person = []  # 历史事件-人物关系
        self.rels_event_mission = []  # 历史事件-任务关系
        self.rels_event_port = []  # 历史事件-港口关系
        self.rels_person_ship = []  # 人物-船只关系
        self.rels_country_port = []  # 国家-港口关系
        self.rels_person_country = []  # 人物-国家关系
        self.rels_ship_mission = []  # 船只-任务关系
        self.rels_port_connection = []  # 港口-港口关系

    def extract_triples(self, data_path):
        print("从json文件中转换抽取三元组")
        with open(data_path, 'r', encoding='utf8') as f:
            for line in tqdm(f.readlines(), ncols=80):
                data_json = json.loads(line)
                event = data_json['event_name']
                self.historical_events.append(event)

                # 提取国家
                if 'countries' in data_json:
                    countries = data_json['countries']
                    self.countries += countries
                    for country in countries:
                        self.rels_event_country.append([event, 'happened_in', country])

                # 提取年份
                if 'year' in data_json:
                    year = data_json['year']
                    self.years.append(year)
                    self.rels_event_year.append([event, 'occurred_in_year', year])

                # 提取人物
                if 'persons' in data_json:
                    persons = data_json['persons']
                    self.persons += persons
                    for person in persons:
                        self.rels_event_person.append([event, 'involved_person', person])

                # 提取任务
                if 'missions' in data_json:
                    missions = data_json['missions']
                    self.missions += missions
                    for mission in missions:
                        self.rels_event_mission.append([event, 'involved_mission', mission])

                # 提取港口
                if 'ports' in data_json:
                    ports = data_json['ports']
                    self.ports += ports
                    for port in ports:
                        self.rels_event_port.append([event, 'involved_port', port])

                # 提取船只
                if 'ships' in data_json:
                    ships = data_json['ships']
                    self.ships += ships
                    for ship in ships:
                        for person in persons:
                            self.rels_person_ship.append([person, 'operated_ship', ship])

                # 国家与港口的关系
                if 'country_ports' in data_json:
                    for port, country in data_json['country_ports']:
                        self.rels_country_port.append([port, 'located_in', country])

                # 人物与国籍的关系
                if 'person_country' in data_json:
                    for person, country in data_json['person_country']:
                        self.rels_person_country.append([person, 'belongs_to', country])

                # 船只与任务的关系
                if 'ship_missions' in data_json:
                    for ship, mission in data_json['ship_missions']:
                        self.rels_ship_mission.append([ship, 'carried_out_mission', mission])

                # 港口之间的连接
                if 'port_connections' in data_json:
                    for port1, port2 in data_json['port_connections']:
                        self.rels_port_connection.append([port1, 'connected_to', port2])

    def write_nodes(self, entities, entity_type):
        print("写入 {0} 实体".format(entity_type))
        for node in tqdm(set(entities), ncols=80):
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
        self.write_nodes(self.historical_events, '历史事件')
        self.write_nodes(self.years, '年份')
        self.write_nodes(self.persons, '人物')
        self.write_nodes(self.missions, '任务')
        self.write_nodes(self.ports, '港口')
        self.write_nodes(self.ships, '船只')

    def create_relations(self):
        self.write_edges(self.rels_event_country, '历史事件', '国家')
        self.write_edges(self.rels_event_year, '历史事件', '年份')
        self.write_edges(self.rels_event_person, '历史事件', '人物')
        self.write_edges(self.rels_event_mission, '历史事件', '任务')
        self.write_edges(self.rels_event_port, '历史事件', '港口')
        self.write_edges(self.rels_person_ship, '人物', '船只')
        self.write_edges(self.rels_country_port, '港口', '国家')
        self.write_edges(self.rels_person_country, '人物', '国家')
        self.write_edges(self.rels_ship_mission, '船只', '任务')
        self.write_edges(self.rels_port_connection, '港口', '港口')

    def export_data(self, data, path):
        if isinstance(data[0], str):
            data = sorted([d.strip("...") for d in set(data)])
        with codecs.open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def export_entities_relations(self):
        self.export_data(self.countries, './graph_data/countries.json')
        self.export_data(self.historical_events, './graph_data/historical_events.json')
        self.export_data(self.years, './graph_data/years.json')
        self.export_data(self.persons, './graph_data/persons.json')
        self.export_data(self.missions, './graph_data/missions.json')
        self.export_data(self.ports, './graph_data/ports.json')
        self.export_data(self.ships, './graph_data/ships.json')

        self.export_data(self.rels_event_country, './graph_data/rels_event_country.json')
        self.export_data(self.rels_event_year, './graph_data/rels_event_year.json')
        self.export_data(self.rels_event_person, './graph_data/rels_event_person.json')
        self.export_data(self.rels_event_mission, './graph_data/rels_event_mission.json')
        self.export_data(self.rels_event_port, './graph_data/rels_event_port.json')
        self.export_data(self.rels_person_ship, './graph_data/rels_person_ship.json')
        self.export_data(self.rels_country_port, './graph_data/rels_country_port.json')
        self.export_data(self.rels_person_country, './graph_data/rels_person_country.json')
        self.export_data(self.rels_ship_mission, './graph_data/rels_ship_mission.json')
        self.export_data(self.rels_port_connection, './graph_data/rels_port_connection.json')

if __name__ == '__main__':
    path = "./graph_data/maritime_history.json"
    extractor = MaritimeHistoryExtractor()
    extractor.extract_triples(path)
    extractor.create_entities()
    extractor.create_relations()
    extractor.export_entities_relations()

