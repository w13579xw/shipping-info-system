from db import get_graph
from entity_kb import (historical_events, countries, missions, persons, ports, ships, years)

# 各类实体（航线、国家、任务、人物、港口、船只、年份）见 entity_kb.py

# Neo4j 连接延迟创建：首次查询时才真正连接，
# 避免「导入本模块」这一动作依赖 Neo4j 在线。
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = get_graph()
    return _graph


# 执行Cypher查询
def execute_cypher_query(cypher_query):
    result = _get_graph().run(cypher_query)  # 执行查询
    return result

# 实体识别和问题解析
def parse_question(question):
    entities = {
        "航线": None,
        "船只": None,
        "港口": None,
        "任务": None,
        "年份": None,
        "负责人": None,
        "国家": None
    }

    # 历史事件
    for historical_event in historical_events:
        if historical_event in question:
            entities["航线"] = historical_event
            break

    # 国家
    for country in countries:
        if country in question:
            entities["国家"] = country
            break

    # 根据任务名称识别任务
    for mission in missions:
        if mission in question:
            entities["任务"] = mission
            break

    # 根据人物名称识别负责人
    for person in persons:
        if person in question:
            entities["负责人"] = person
            break

    # 根据港口名称识别港口
    for port in ports:
        if port in question:
            entities["港口"] = port
            break

    # 根据船只名称识别船只
    for ship in ships:
        if ship in question:
            entities["船只"] = ship
            break

    # 根据年份识别年份
    for year in years:
        if year in question:
            entities["年份"] = year
            break

    # 根据问题的不同，确定查询类型
    if "港口" in question:
        if entities["国家"]:
            query_type = "ports_by_country"
        else:
            query_type = "ports"
    elif "负责人" in question:
        query_type = "person"
    elif "任务" in question:
        query_type = "mission"
    elif "事件" in question:
        query_type = "event_by_country"
    elif "国家" in question:
        if entities["港口"]:
            query_type = "country_by_ports"
    else:
        query_type = "unknown"

    return entities, query_type

# 构建Cypher查询
def build_cypher_query(entities, query_type):
    if query_type == "ports":
        cypher_query = f"""
        MATCH (e:历史事件)-[:involved_port]->(p:港口)
        WHERE toLower(e.name) CONTAINS toLower('{entities["航线"]}')
        RETURN p.name AS 港口
        """
    elif query_type == "person":
        cypher_query = f"""
        MATCH (e:历史事件)-[:involved_person]->(p:人物)
        WHERE toLower(e.name) CONTAINS toLower('{entities["航线"]}')
        RETURN p.name AS 负责人
        """
    elif query_type == "mission":
        cypher_query = f"""
        MATCH (s:船只)-[:carried_out_mission]->(m:任务)
        WHERE toLower(s.name) CONTAINS toLower('{entities["船只"]}')
        RETURN m.name AS 任务
        """
    elif query_type == "event_by_country":
        cypher_query = f"""
        MATCH (e:历史事件)-[:happened_in]->(c:国家)
        WHERE toLower(c.name) = toLower('{entities["国家"]}')
        RETURN e.name AS 事件
        """
    elif query_type == "ports_by_country":
        cypher_query = f"""
        MATCH (e:港口)-[:located_in]->(c:国家)
        WHERE toLower(c.name) = toLower('{entities["国家"]}')
        RETURN e.name AS 港口
        """
    elif query_type == "country_by_ports":
        cypher_query = f"""
        MATCH (e:港口)-[:located_in]->(c:国家)
        WHERE toLower(e.name) = toLower('{entities["港口"]}')
        RETURN c.name AS 国家
        """
    else:
        cypher_query = "RETURN '无法回答您的问题' AS 结果"

    return cypher_query

# 处理用户输入
def process_question(question):
    entities, query_type = parse_question(question)
    cypher_query = build_cypher_query(entities, query_type)

    print(question)
    print(f"执行的Cypher查询：\n{cypher_query}")

    output = []  # 用于与前端交互

    result = execute_cypher_query(cypher_query)
    for record in result:
        print(record)
        output.append(record[0])

    return output



if __name__ == '__main__':
    # 示例：查询“中美贸易航线的主要港口有哪些？”
    process_question("中美贸易航线的主要港口有哪些？")

    # 示例：查询“谁是亚太地区航运整合的负责人？”
    process_question("谁是亚太地区航运整合的负责人？")

    # 示例：查询“长赐号的任务是什么？”
    process_question("长赐号的任务是什么？")

    # 示例：查询“中国的历史事件有哪些？”
    process_question("中国的历史事件有哪些？")

    # 示例：查询“中国的港口有哪些？”
    process_question("中国的港口有哪些？")

    # 查询“东京港是哪个国家的？”
    process_question("东京港是哪个国家的？")
