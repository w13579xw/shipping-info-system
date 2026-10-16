from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from app01.models import Post, Comment

def forum_list(request):
    """论坛帖子列表"""
    # 记录模块访问
    from app01.models import ModuleVisit, UserInfo
    from django.db.models import Count
    user = None
    if request.session.get('user_info'):
        user = UserInfo.objects.get(id=request.session['user_info']['id'])
    ModuleVisit.objects.create(module_name='forum', user=user)

    filter_type = request.GET.get('filter', 'all')
    sort_by = request.GET.get('sort', 'latest')
    user_id = request.session.get('user_info', {}).get('id')

    # 基础查询集
    if filter_type == 'my_posts' and user_id:
        posts = Post.objects.filter(author_id=user_id)
    elif filter_type == 'my_comments' and user_id:
        posts = Post.objects.filter(comments__author_id=user_id).distinct()
    else:
        posts = Post.objects.all()

    # 添加评论数注释
    posts = posts.annotate(comment_count=Count('comments'))

    # 排序处理
    if sort_by == 'most_comments':
        posts = posts.order_by('-comment_count', '-created_at')
    else:  # 默认按最新发布时间排序
        posts = posts.order_by('-created_at')

    # 预加载评论
    posts = posts.prefetch_related('comments')

    context = {
        'posts': posts,
        'filter_type': filter_type,
        'sort_by': sort_by
    }
    return render(request, 'forum/forum_list.html', context)

def post_detail(request, post_id):
    """帖子详情"""
    post = Post.objects.get(id=post_id)
    comments = post.comments.all()
    return render(request, 'forum/post_detail.html', {'post': post, 'comments': comments})

def post_add(request):
    """发布帖子"""
    if request.method == 'GET':
        return render(request, 'forum/post_add.html')
    
    if not request.session.get('user_info'):
        messages.error(request, '请先登录')
        return redirect('/user/login')
    
    title = request.POST.get('title')
    content = request.POST.get('content')
    user_id = request.session['user_info']['id']
    
    Post.objects.create(
        title=title,
        content=content,
        author_id=user_id
    )
    return redirect('/forum/list')

def comment_add(request, post_id):
    """添加评论"""
    if not request.session.get('user_info'):
        messages.error(request, '请先登录')
        return redirect('/user/login')
    
    content = request.POST.get('content')
    user_id = request.session['user_info']['id']
    
    Comment.objects.create(
        content=content,
        author_id=user_id,
        post_id=post_id
    )
    return redirect(f'/forum/post/{post_id}')

def post_delete(request, post_id):
    """删除帖子"""
    if not request.session.get('user_info'):
        return JsonResponse({'status': 'error', 'message': '请先登录'})
    
    try:
        post = Post.objects.get(id=post_id)
        if post.author_id != request.session['user_info']['id']:
            return JsonResponse({'status': 'error', 'message': '只能删除自己的帖子'})
        
        post.delete()
        return JsonResponse({'status': 'success', 'message': '删除成功'})
    except Post.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '帖子不存在'})

from django.views.decorators.csrf import csrf_protect

@csrf_protect
def comment_delete(request, comment_id):
    """删除评论"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '不支持的请求方法'})
    
    if not request.session.get('user_info'):
        return JsonResponse({'status': 'error', 'message': '请先登录'})
    
    try:
        comment = Comment.objects.get(id=comment_id)
        if comment.author_id != request.session['user_info']['id']:
            return JsonResponse({'status': 'error', 'message': '只能删除自己的评论'})
        
        post_id = comment.post_id
        comment.delete()
        return JsonResponse({'status': 'success', 'message': '删除成功', 'post_id': post_id})
    except Comment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '评论不存在'})