from django.shortcuts import render
from app01.models import Post
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def index(request):
    # 设置固定的港口和船舶数量
    port_count = 3238
    ship_count = 9600

    # 从MongoDB获取资讯总数（MongoDB 不可用时降级为 0，保证首页可用）
    news_count = 0
    try:
        client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
        db = client[settings.MONGODB_NAME]
        collection = db[settings.MONGODB_COLLECTION]
        news_count = collection.count_documents({})
        client.close()
    except PyMongoError as e:
        print(f'[index] MongoDB 不可用：{e}')

    # 获取论坛帖子总数
    post_count = Post.objects.count()

    context = {
        'port_count': port_count,
        'ship_count': ship_count,
        'news_count': news_count,
        'post_count': post_count
    }

    return render(request, 'index.html', context)