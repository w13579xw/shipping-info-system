#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import time

import requests
from bs4 import BeautifulSoup
import re
import json

USERAGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'

# 定义一个变量url，为需要爬取数据我网页网址
url = 'http://gangkou.00cha.net/'

# 获取这个网页的源代码，存放在req中，{}中为不同浏览器的不同User-Agent属性，针对不同浏览器可以自行百度
req = requests.get(url, {
    'User-Agent': USERAGENT})
req.encoding = 'gb2312'
# 生成一个Beautifulsoup对象，用以后边的查找工作
soup = BeautifulSoup(req.text, 'lxml')

# 找到所有a标签中的内容并存放在xml这样一个类似于数组队列的对象中
gjls = []


# 查找国家港口的URL
gkcnt = 0
allgkcnt = 0

# 找到特定的div元素
div_element = soup.find_all('div', class_='bei lh')
if div_element:
    # 找到所有的a标签
    xmlgj = div_element[2].find_all('a')
    for k in xmlgj:
        if 'gj_' in k['href']:
            gjls.append(k['href'])
print(f'总共有 {len(gjls)} 个国家。')

# 遍历每个国家
for gj in gjls:
    print(f"{gj.split('_')[1].replace('.html', '')}")
    gkls = []
    urlgj = url + gj
    reqgj = requests.get(urlgj, {
        'User-Agent': USERAGENT})
    reqgj.encoding = 'gb2312'
    soupgj = BeautifulSoup(reqgj.text, 'lxml')
    table_element = soupgj.find_all('table', class_='tablea')
    if table_element:
        xmlgk = table_element[0].find_all('a')
        for k in xmlgk:
            if 'gk_' in k['href']:
                gkls.append(k['href'])
    print(f'该国家总共有 {len(gkls)} 个港口。')
    allgkcnt += len(gkls)
    gkcnt = 0
    # 对于每个国家遍历每个港口
    for gk in gkls:
        gkcnt += 1
        urlgk = url + gk
        reqgk = requests.get(urlgk, {
            'User-Agent': USERAGENT})
        reqgk.encoding = 'gb2312'
        soupgk = BeautifulSoup(reqgk.text, 'lxml')
        trarry = []
        for tr in soupgk.find_all('tr'):
            tdarry = []
            for td in tr.find_all('td'):
                text = td.text.replace('\u3000', '').replace('&nbsp;', ' ')
                tdarry.append(text)
            trarry.append(tdarry)

        # 展平table_data为字典
        port_data_flat = {}
        for row in trarry:
            if len(row) >= 2:  # 确保至少有一个键值对
                for i in range(0, len(row) - 1, 2):  # 每次跳过2个元素，形成键值对
                    key = row[i]  # 这是2n-1位置的元素
                    value = row[i + 1]  # 这是紧接着的2n位置的元素
                    port_data_flat[key] = value

        # 提取城市和国家的中文与英文
        city_info = port_data_flat.get('城市', '').split(' ')
        country_info = port_data_flat.get('国家', '').split(' ')

        # 创建一个字典来存储数据
        port_data = {
            '港口代码': port_data_flat.get('港口代码', ''),
            '城市中文': city_info[1] if len(city_info) > 1 else '',
            '城市英文': city_info[0] if len(city_info) > 0 else '',
            '港口中文': port_data_flat.get('港口中文', ''),
            '港口英文': port_data_flat.get('港口英文', ''),
            '国家中文': country_info[0] if len(country_info) > 0 else '',
            '国家英文': country_info[1] if len(country_info) > 1 else '',
            '地区': port_data_flat.get('地区', ''),
            '航线中文': port_data_flat.get('航线中文', ''),
            '航线英文': port_data_flat.get('航线英文', '')
        }

        # 直接将数据追加到JSON文件末尾
        with open('port_data.json', 'a', encoding='utf-8') as json_file:
            # 如果文件为空，写入一个空的JSON数组
            if os.path.getsize('port_data.json') == 0:
                json_file.write('[')
            else:
                json_file.seek(json_file.tell() - 1, os.SEEK_SET)  # 移动到倒数第二个字符（去掉最后一个]）
                json_file.truncate()  # 删除最后一个]
                json_file.write(',\n')  # 添加逗号和换行符
            json.dump(port_data, json_file, ensure_ascii=False, indent=4)
            json_file.write(']')  # 添加结束的]

        # 输出港口已入库信息
        print(f"第{gkcnt}条数据：{port_data['港口中文']} 已入库")

        # 增加请求间隔时间
        time.sleep(0.2)  # 增加爬取间隔时间


print(f'总共 {allgkcnt} 个港口')
