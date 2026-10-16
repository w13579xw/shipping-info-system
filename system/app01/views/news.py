from django.http import JsonResponse
from django.shortcuts import render
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from django.conf import settings
from bson import ObjectId
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from collections import Counter
from functools import wraps
from app01.models import NewsHistory, UserInfo, ModuleVisit
from django.contrib.auth.decorators import login_required
from django.db.models import Count

# 连接MongoDB数据库（设置较短的连接超时，避免服务不可用时请求长时间挂起）
client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
db = client[settings.MONGODB_NAME]
collection = db[settings.MONGODB_COLLECTION]


def _mongo_guard(func):
    """MongoDB 不可用时的统一降级处理：返回友好的错误提示而非 500。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PyMongoError as e:
            print(f'[news] MongoDB 错误：{e}')
            return JsonResponse({'success': False, 'message': '资讯数据库暂不可用，请稍后重试', 'data': []})
    return wrapper

def news_list(request):
    """咨询列表页面"""
    # 记录模块访问
    from app01.models import ModuleVisit, UserInfo
    user = None
    if request.session.get('user_info'):
        user = UserInfo.objects.get(id=request.session['user_info']['id'])
    ModuleVisit.objects.create(module_name='news_query', user=user)
    
    # 获取热门关键词
    hot_keywords = get_hot_keywords()
    return render(request, 'news_list.html', {'hot_keywords': hot_keywords})

@_mongo_guard
def news_api_list(request):
    """获取咨询列表数据API"""
    # 获取查询参数
    keyword = request.GET.get('keyword', '')
    try:
        # 确保page从1开始
        page = max(1, int(request.GET.get('page', 1)))
        page_size = int(request.GET.get('page_size', 10))
    except ValueError:
        page = 1
        page_size = 10
    sort_direction = request.GET.get('sort', 'desc')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # 记录查询参数
    print(f"[{datetime.now()}] Query params: page={page}, page_size={page_size}, sort={sort_direction}, start_date={start_date}, end_date={end_date}, keyword={keyword}")
    
    # 构建查询条件
    query = {}
    if keyword:
        query['$or'] = [
            {'title': {'$regex': keyword, '$options': 'i'}},
            {'keywords': {'$regex': keyword, '$options': 'i'}}
        ]
    
    # 添加日期范围查询
    if start_date or end_date:
        query['date'] = {}
        if start_date:
            try:
                query['date']['$gte'] = start_date
            except ValueError:
                print(f"[{datetime.now()}] Invalid start_date format: {start_date}")
        if end_date:
            try:
                query['date']['$lte'] = end_date
            except ValueError:
                print(f"[{datetime.now()}] Invalid end_date format: {end_date}")
    
    # 查询数据并排序
    total = collection.count_documents(query)
    skip = (page - 1) * page_size
    news_data = list(collection.find(query, {
        'title': 1,
        'summary': 1,
        'date': 1,
        'keywords': 1,
        'body': 1
    }).sort('date', -1 if sort_direction == 'desc' else 1).skip(skip).limit(page_size))
    
    # 记录查询结果
    print(f"[{datetime.now()}] Query result: total={total}, returned={len(news_data)}, skip={skip}, limit={page_size}")
    
    # 处理数据格式
    for news in news_data:
        news['id'] = str(news.pop('_id'))
        if 'date' in news:
            news['date'] = news['date'].strftime('%Y-%m-%d') if isinstance(news['date'], datetime) else news['date']
    
    # 返回分页数据
    return JsonResponse({
        'success': True,
        'data': {
            'list': news_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    }, safe=False)

def get_hot_keywords(limit=20):
    """获取热门关键词统计"""
    try:
        # 从数据库中获取所有新闻的关键词
        all_news = collection.find({}, {'keywords': 1})

        # 统计关键词频率
        keyword_counter = Counter()
        for news in all_news:
            if 'keywords' in news and news['keywords']:
                # 将关键词字符串分割成列表
                keywords = [kw.strip() for kw in news['keywords'].split()]
                keyword_counter.update(keywords)

        # 获取出现频率最高的关键词
        return [{'keyword': kw, 'count': count} for kw, count in keyword_counter.most_common(limit)]
    except PyMongoError as e:
        print(f'[news] 获取热门关键词失败：{e}')
        return []

@_mongo_guard
def get_user_news_history(request):
    """获取用户的新闻浏览历史API"""
    if not request.session.get('user_info'):
        return JsonResponse({'success': False, 'error': '用户未登录'}, status=401)
    
    try:
        page = max(1, int(request.GET.get('page', 1)))
        page_size = int(request.GET.get('page_size', 10))
    except ValueError:
        page = 1
        page_size = 10
    
    user = UserInfo.objects.get(id=request.session['user_info']['id'])
    history = NewsHistory.objects.filter(user=user).order_by('-view_time')
    
    # 去除连续重复的新闻，只保留最新的一条
    filtered_history = []
    prev_news_id = None
    for item in history:
        if item.news_id != prev_news_id:
            filtered_history.append(item)
        prev_news_id = item.news_id
    
    paginator = Paginator(filtered_history, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取所有历史记录的新闻ID
    news_ids = [item.news_id for item in page_obj]
    # 从MongoDB中获取这些新闻的关键词信息
    news_keywords = {
        str(news['_id']): news.get('keywords', '')
        for news in collection.find({'_id': {'$in': [ObjectId(nid) for nid in news_ids]}}, {'keywords': 1})
    }
    
    history_list = [{
        'news_id': item.news_id,
        'title': item.title,
        'view_time': item.view_time.strftime('%Y-%m-%d'),
        'keywords': news_keywords.get(item.news_id, '')  # 添加关键词信息
    } for item in page_obj]
    
    return JsonResponse({
        'success': True,
        'data': {
            'list': history_list,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
    })

@_mongo_guard
def get_recommended_news(request):
    """获取个性化推荐新闻API"""
    if not request.session.get('user_info'):
        return JsonResponse({'success': False, 'error': '用户未登录'}, status=401)
    
    user = UserInfo.objects.get(id=request.session['user_info']['id'])
    
    # 获取用户所有浏览历史，用于排除
    all_history = NewsHistory.objects.filter(user=user)
    viewed_news_ids = [history.news_id for history in all_history]
    
    # 获取用户浏览历史的新闻关键词
    recent_history = NewsHistory.objects.filter(user=user).order_by('-view_time')
    recent_news_ids = [history.news_id for history in recent_history]
    
    # 获取这些新闻的关键词
    news_list = list(collection.find({'_id': {'$in': [ObjectId(nid) for nid in recent_news_ids]}}))    
    keywords = []
    for news in news_list:
        if 'keywords' in news and news['keywords']:
            keywords.extend([kw.strip() for kw in news['keywords'].split()])
    
    # 统计关键词频率并计算权重
    keyword_counter = Counter(keywords)
    total_keywords = sum(keyword_counter.values())
    keyword_weights = {k: v/total_keywords for k, v in keyword_counter.items()}
    
    # 基于关键词权重和时效性推荐新闻
    recommended_news = []
    if keyword_weights:
        # 排除已浏览的新闻
        query = {
            '_id': {'$nin': [ObjectId(nid) for nid in viewed_news_ids]}
        }
        
        # 获取候选新闻
        candidate_news = list(collection.find(query))
        
        # 计算每条新闻的推荐分数
        scored_news = []
        for news in candidate_news:
            score = 0
            if 'keywords' in news and news['keywords']:
                news_keywords = [kw.strip() for kw in news['keywords'].split()]
                # 计算关键词匹配度
                for kw in news_keywords:
                    if kw in keyword_weights:
                        score += keyword_weights[kw]
                
                # 考虑时效性，使用相对时间差计算得分
                if isinstance(news['date'], str):
                    news_date = datetime.strptime(news['date'], '%Y-%m-%d')
                else:
                    news_date = news['date']
                time_diff = (datetime.now() - news_date).total_seconds()
                # 使用指数衰减函数计算时间得分，避免硬性时间限制
                time_score = 1 / (1 + time_diff / (7 * 24 * 3600))  # 使用一周作为时间衰减的基准单位
                
                final_score = score * 0.7 + time_score * 0.3  # 权重可以根据需要调整
                scored_news.append((news, final_score))
        
        # 按分数排序并选择前10条新闻
        scored_news.sort(key=lambda x: x[1], reverse=True)
        recommended_news = [news for news, score in scored_news[:10]]
        
        # 处理数据格式
        for news in recommended_news:
            news['id'] = str(news.pop('_id'))
            if 'date' in news:
                news['date'] = news['date'].strftime('%Y-%m-%d') if isinstance(news['date'], datetime) else news['date']
    
    return JsonResponse({
        'success': True,
        'data': recommended_news
    })

def news_api_detail(request, news_id):
    """获取咨询详情数据API"""
    try:
        news = collection.find_one({'_id': ObjectId(news_id)})
        if news:
            # 如果用户已登录，记录浏览历史
            if request.session.get('user_info'):
                from app01.models import NewsHistory, UserInfo
                user = UserInfo.objects.get(id=request.session['user_info']['id'])
                NewsHistory.objects.create(
                    user=user,
                    news_id=str(news['_id']),
                    title=news.get('title', '')
                )
            
            data = {
                'success': True,
                'data': {
                    'title': news.get('title', ''),
                    'content': news.get('body', ''),  # 使用body字段作为内容
                    'date': news['date'].strftime('%Y-%m-%d') if isinstance(news.get('date'), datetime) else news.get('date', ''),
                    'keywords': news.get('keywords', '')  # 添加关键词字段
                }
            }
            return JsonResponse(data)
        return JsonResponse({'success': False, 'error': '咨询不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_hot_news(request):
    """获取热门资讯API"""
    try:
        # 从NewsHistory中统计所有新闻的访问量
        news_views = NewsHistory.objects.values('news_id').annotate(
            views=Count('news_id')
        ).order_by('-views')[:10]  # 只获取访问量最高的10条记录
        
        # 获取热门新闻的ID列表
        hot_news_ids = [item['news_id'] for item in news_views]
        
        # 从MongoDB中获取这些新闻的详细信息
        news_list = []
        if not hot_news_ids:
            return JsonResponse({
                'success': True,
                'data': []
            })
            
        for news in collection.find({'_id': {'$in': [ObjectId(nid) for nid in hot_news_ids]}}):
            # 处理日期格式
            date_str = ''
            try:
                if 'date' in news:
                    if isinstance(news['date'], datetime):
                        date_str = news['date'].strftime('%Y-%m-%d')
                    elif isinstance(news['date'], str):
                        # 尝试解析字符串日期
                        date_str = datetime.strptime(news['date'], '%Y-%m-%d').strftime('%Y-%m-%d')
                    else:
                        date_str = str(news.get('date', ''))
            except (ValueError, TypeError):
                date_str = ''
                
            news_data = {
                'id': str(news['_id']),
                'title': news.get('title', ''),
                'date': date_str,
                'views': next((item['views'] for item in news_views if item['news_id'] == str(news['_id'])), 0),
                'keywords': news.get('keywords', '')  # 添加关键词字段
            }
            news_list.append(news_data)
        
        # 按访问量排序
        news_list.sort(key=lambda x: x['views'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'data': news_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def news_recommended(request):
    """个性推荐页面"""
    # 记录模块访问
    user = None
    if request.session.get('user_info'):
        user = UserInfo.objects.get(id=request.session['user_info']['id'])
    ModuleVisit.objects.create(module_name='news_recommended', user=user)
    return render(request, 'news_recommended.html')


def news_api_search_bm25(request):
    """BM25检索API"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({
            'success': False,
            'message': '请输入搜索关键词'
        })

    try:
        # 从MongoDB获取所有文档
        documents = list(collection.find({}, {
            'title': 1,
            'content': 1,
            'date': 1,
            'keywords': 1
        }))

        # 准备文档集合
        corpus = [f"{doc.get('title', '')} {doc.get('content', '')}" for doc in documents]

        # 创建BM25实例并执行搜索
        from app01.utils.bm25 import bm25_search
        search_results = bm25_search(
            corpus=corpus,
            query=query,
            language='mixed',
            top_k=10
        )

        # 处理搜索结果
        result_data = []
        for doc_id, score, _ in search_results:
            doc = documents[doc_id]
            result_data.append({
                'id': str(doc['_id']),
                'title': doc.get('title', ''),
                'date': doc['date'].strftime('%Y-%m-%d') if isinstance(doc['date'], datetime) else doc['date'],
                'keywords': doc.get('keywords', ''),
                'score': score
            })

        return JsonResponse({
            'success': True,
            'data': result_data
        })

    except Exception as e:
        print(f"BM25搜索错误: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '搜索过程中发生错误'
        })