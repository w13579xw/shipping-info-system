#!/usr/bin/env python
# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup
import requests
from pymongo import MongoClient
import time
import re

# 配置MongoDB连接
client = MongoClient('mongodb://localhost:27017/')  # 连接到本地MongoDB实例
db = client['news_db']  # 使用或创建一个名为news_db的数据库
collection = db['news_collection']  # 使用或创建一个集合（表）来保存新闻


def clean_text(text):
    """
    清理文本中的多余空行，保留正常换行符。
    删除含有特定声明文本的内容。
    :param text: 原始文本
    :return: 清理后的文本
    """
    # 删除含有特定声明文本的内容
    text = re.sub(r'声明：.*', '', text, flags=re.DOTALL)
    text = re.sub(r'航运在线编译整理', '', text)

    # 替换多个换行符为单个换行符
    text = re.sub(r'\n\s*\n', '\n', text)

    return text


def fetch_article_details(article_url, retry=3):
    """
    获取指定新闻链接的文章详情（正文和关键字）
    :param article_url: 新闻详情页的URL
    :param retry: 最大重试次数
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while retry > 0:
        try:
            response = requests.get(article_url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            content_div = soup.find('div', id='content')
            if not content_div:
                return None, None

            # 获取正文
            paragraphs = content_div.find_all('p')
            body = "\n".join([para.get_text() for para in paragraphs])
            body = clean_text(body)  # 清理正文中的多余空行

            # 获取关键字
            keyword_div = content_div.find('div', class_='newslist-box-keyword')
            keyword = keyword_div.find('div', class_='newslist-box-keyword-text').get_text(strip=True) if keyword_div else "无"

            return body, keyword
        except Exception as e:
            print(f"获取文章详情时出错: {e}, 尝试重试...")
            retry -= 1
            time.sleep(2)  # 在每次重试前等待2秒
    return None, None


def process_news_item(news_item):
    """
    处理单个新闻项，获取详情并保存到MongoDB
    :param news_item: 包含新闻链接、标题和日期的字典
    """
    article_url = "https://news.sol.com.cn" + news_item['url']
    print(f"正在处理新闻: {news_item['title']} ({article_url})")

    body, keywords = fetch_article_details(article_url)

    if body and keywords:
        # 准备要插入MongoDB的数据
        news_data = {
            'title': news_item['title'],
            'date': news_item['date'],
            'body': body,
            'keywords': keywords
        }

        # 插入数据到MongoDB
        collection.insert_one(news_data)
        print(f"已保存新闻: {news_item['title']} 到 MongoDB")

        # 增加等待时间
        time.sleep(3)  # 在每次插入数据库后等待3秒
    else:
        print(f"无法获取新闻内容: {news_item['title']}")


def extract_news_info(url, retry=3):
    """
    从给定的URL中提取新闻资讯信息，并使用自定义的User-Agent。
    :param url: 网站的URL
    :param retry: 最大重试次数
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while retry > 0:
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 初始化列表以保存提取的信息
            news_items = []

            # 查找包含“即时资讯”的div，然后找到其下的ul中的所有li
            for ul in soup.select('div.flzx-gshsc-newplzx div.box-newplzx-list ul'):
                for li in ul.find_all('li'):
                    try:
                        # 提取<a>标签内的href属性值作为新闻链接
                        a_tag = li.find('a')
                        if not a_tag:
                            continue  # 如果没有找到<a>标签，则跳过该<li>

                        news_link = a_tag['href']
                        title = a_tag.get_text(strip=True)

                        # 尝试获取时间，如果没有找到<span class="time">则设为未知
                        time_span = li.find('span', class_='time')
                        news_time = time_span.get_text(strip=True) if time_span else "未知时间"

                        # 将信息添加到列表中
                        news_items.append({
                            'url': news_link,
                            'title': title,
                            'date': news_time
                        })
                    except Exception as e:
                        print(f"处理新闻项时出错: {e}")
                        continue  # 遇到任何异常都继续处理下一个<li>
            return news_items
        except Exception as e:
            print(f"获取页面信息时出错: {e}, 尝试重试...")
            retry -= 1
            time.sleep(2)  # 在每次重试前等待2秒
    return []


# 定义起始和结束页码
start_page = 1
end_page = 620

base_url = "https://news.sol.com.cn/shipping_comprehensive/index.asp?pageno="

for page in range(start_page, end_page + 1):
    url = f"{base_url}{page}"
    print(f"正在爬取第{page}页: {url}")

    # 提取当前页面上的新闻列表
    news_infos = extract_news_info(url)

    # 对每条新闻进行处理，包括获取详情和保存到MongoDB
    for news_item in news_infos:
        process_news_item(news_item)

    time.sleep(1)  # 每次请求后等待1秒以减少服务器压力

print("所有新闻均已成功保存到MongoDB")




# 输出测试

# from bs4 import BeautifulSoup
# import requests
# import time
# import re
#
#
# def clean_text(text):
#     """
#     清理文本中的多余空行，保留正常换行符。
#     删除含有特定声明文本的内容。
#     :param text: 原始文本
#     :return: 清理后的文本
#     """
#     # 删除含有特定声明文本的内容
#     text = re.sub(r'声明：.*', '', text, flags=re.DOTALL)
#     text = re.sub(r'航运在线编译整理', '', text)
#
#     # # 将HTML标签去除
#     # text = re.sub(r'<[^>]+>', '', text)
#
#     # 替换多个换行符为单个换行符，并去掉每行开头结尾的空白字符
#     text = re.sub(r'\n\s*\n', '\n', text)
#     # # 压缩行内连续的空白字符（包括空格、制表符等），不包括换行符
#     # text = re.sub(r'(?<!\n)[\s]{2,}(?!\n)', ' ', text)
#
#     return text
#
# def extract_news_info(url):
#     """
#     从给定的URL中提取新闻资讯信息，并使用自定义的User-Agent。
#     :param url: 网站的URL
#     """
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#
#     response = requests.get(url, headers=headers)
#     soup = BeautifulSoup(response.content, 'html.parser')
#
#     # 初始化列表以保存提取的信息
#     news_items = []
#
#     # 查找包含“即时资讯”的div，然后找到其下的ul中的所有li
#     for ul in soup.select('div.flzx-gshsc-newplzx div.box-newplzx-list ul'):
#         for li in ul.find_all('li'):
#             try:
#                 # 提取<a>标签内的href属性值作为新闻链接
#                 a_tag = li.find('a')
#                 if not a_tag:
#                     continue  # 如果没有找到<a>标签，则跳过该<li>
#
#                 news_link = a_tag['href']
#                 title = a_tag.get_text(strip=True)
#
#                 # 尝试获取时间，如果没有找到<span class="time">则设为未知
#                 time_span = li.find('span', class_='time')
#                 news_time = time_span.get_text(strip=True) if time_span else "未知时间"
#
#                 # 将信息添加到列表中
#                 news_items.append({
#                     'url': news_link,
#                     'title': title,
#                     'date': news_time
#                 })
#             except Exception as e:
#                 print(f"处理新闻项时出错: {e}")
#                 continue  # 遇到任何异常都继续处理下一个<li>
#     return news_items
#
#
# def fetch_article_details(article_url):
#     """
#     获取指定新闻链接的文章详情（正文和关键字）
#     :param article_url: 新闻详情页的URL
#     """
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#
#     response = requests.get(article_url, headers=headers)
#     soup = BeautifulSoup(response.content, 'html.parser')
#
#     content_div = soup.find('div', id='content')
#     if not content_div:
#         return None, None
#
#     # 获取正文
#     paragraphs = content_div.find_all('p')
#     body = "\n".join([para.get_text() for para in paragraphs])
#     body = clean_text(body)  # 清理正文中的多余空格
#
#     # 获取关键字
#     keyword_div = content_div.find('div', class_='newslist-box-keyword')
#     keyword = keyword_div.find('div', class_='newslist-box-keyword-text').get_text(strip=True) if keyword_div else "无"
#
#     return body, keyword
#
#
# # 定义起始和结束页码
# start_page = 51
# end_page = 51
#
# all_news_infos = []
# base_url = "https://news.sol.com.cn/shipping_comprehensive/index.asp?pageno="
#
# for page in range(start_page, end_page + 1):
#     url = f"{base_url}{page}"
#     print(f"正在爬取第{page}页: {url}")
#     news_infos = extract_news_info(url)
#     all_news_infos.extend(news_infos)
#     # time.sleep(1)  # 每次请求后等待1秒以减少服务器压力
#
# # 对每条新闻，获取其详细内容
# for news in all_news_infos:
#     article_url = "https://news.sol.com.cn" + news['url']  # 假设新闻链接是相对路径
#     body, keywords = fetch_article_details(article_url)
#     news['body'] = body
#     news['keywords'] = keywords
#     # time.sleep(1)  # 每次请求后等待1秒以减少服务器压力
#
# # 打印结果
# for item in all_news_infos:
#     print(f"标题: {item['title']}")
#     print(f"日期: {item['date']}")
#     print(f"链接: {item['url']}")
#     print(f"正文: {item['body']}")
#     print(f"关键字: {item['keywords']}\n")


