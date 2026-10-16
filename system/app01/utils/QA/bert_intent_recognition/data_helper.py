# -*- coding: utf-8 -*-
import json
import random
import pandas as pd
import matplotlib.pyplot as plt

def gen_sample_base_template():
    # 问候语
    greet_qwds = ['你好，想问一下', '您好，请教下', '请问', '', '', '能帮我查一下', '方便问下']

    # 意图类型词汇模板
    define_qwds = ['的简介', '的介绍', '能简单介绍一下', '有何背景', '是干什么的', '基本信息']
    country_qwds = ['属于哪个国家', '在哪个国家', '是哪个国家的', '归属国家是']
    region_qwds = ['在哪个地区', '属于哪个区域', '在什么地方', '属于哪块']


    # 加载意图标签
    label_list = [line.strip() for line in open('label', 'r', encoding='utf8')]
    label2id = {label: idx for idx, label in enumerate(label_list)}

    # 加载港口实体列表
    port_list = json.load(open('./ports.json', 'r', encoding='utf8'))
    n = len(port_list) - 1

    data = []

    # 定义类问题
    template = "{greet}{port}{define}"
    for i in range(60):
        greet = random.choice(greet_qwds)
        port = port_list[random.randint(0, n)]
        define = random.choice(define_qwds)
        text = template.format(greet=greet, port=port, define=define)
        data.append([text, '港口定义', label2id['港口定义']])

    # 所属国家问题
    template = "{greet}{port}{country}"
    for i in range(60):
        greet = random.choice(greet_qwds)
        port = port_list[random.randint(0, n)]
        country = random.choice(country_qwds)
        text = template.format(greet=greet, port=port, country=country)
        data.append([text, '所属国家', label2id['所属国家']])

    # 所在区域问题
    template = "{greet}{port}{region}"
    for i in range(60):
        greet = random.choice(greet_qwds)
        port = port_list[random.randint(0, n)]
        region = random.choice(region_qwds)
        text = template.format(greet=greet, port=port, region=region)
        data.append([text, '所在区域', label2id['所在区域']])


    return data


def load_data(filename):
    """加载数据（格式：text,label）"""
    df = pd.read_csv(filename, header=0)
    return df[['text', 'label']].values


if __name__ == '__main__':
    # 生成数据
    data = gen_sample_base_template()
    data = pd.DataFrame(data, columns=['text', 'label_class', 'label'])

    # 打乱顺序
    data = data.sample(frac=1.0)

    # 查看类别分布
    print(data['label_class'].value_counts())

    # 查看文本长度分布
    data['text_len'] = data['text'].map(lambda x: len(x))
    print(data['text_len'].describe())

    # 绘制长度直方图
    plt.hist(data['text_len'], bins=30, rwidth=0.9, density=True)
    plt.title("Text Length Distribution")
    plt.xlabel("Length")
    plt.ylabel("Density")
    plt.show()

    del data['text_len']

    # 划分训练集与测试集（90%:10%）
    train_num = int(0.9 * len(data))
    train, test = data[:train_num], data[train_num:]

    # 保存为CSV
    train.to_csv("./data/train.csv", index=False)
    test.to_csv("./data/test.csv", index=False)
