"""myProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.views.static import serve
from django.shortcuts import render
from app01.views import user, admin, chart, ship, qa, register, news, forum, account, index

urlpatterns = [
    # 媒体文件服务
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name='media'),

    # 主页
    path('', index.index),

    # 用户管理
    path('user/list', user.user_lst),
    path('user/add', user.user_add),
    path('user/<int:user_id>/edit', user.user_edit),
    path('user/<int:user_id>/del', user.user_del),

    # 管理员管理
    path('admin/list', admin.admin_lst),
    path('admin/add', admin.admin_add),
    path('admin/<int:admin_id>/del', admin.admin_del),
    path('admin/<int:admin_id>/edit', admin.admin_edit),
    path('admin/<int:admin_id>/reset', admin.admin_reset),

    # 账户
    path('admin/login', account.login),
    path('admin/logout', account.logout),
    path('user/login', user.user_login),
    path('user/register', register.register),
    path('user/logout', user.user_logout),
    path('image/code', user.image_code),
    path('user/save_redirect_url', user.save_redirect_url),

    # 数据统计
    path('chart/list', chart.chart_list),
    path('chart/module-line', chart.module_line),
    path('chart/module-pie', chart.module_pie),
    path('chart/user-bar', chart.user_bar),
    path('chart/activity-stack', chart.activity_stack),

    # 船舶识别
    path('ship/identify', ship.identify),
    path('ship/detect', ship.detect_ship),

    # 航运问答
    path('qa', qa.qa_page),
    path('qa/ask', qa.ask_question),

    # 咨询列表
    path('news/list', news.news_list),
    path('news/api/list', news.news_api_list),
    path('news/api/detail/<str:news_id>', news.news_api_detail),
    
    # 个性推荐
    path('news/recommended', news.news_recommended),
    path('news/api/history', news.get_user_news_history),
    path('news/api/recommended', news.get_recommended_news),
    path('news/api/hot', news.get_hot_news),
    path('news/api/search/bm25', news.news_api_search_bm25),

    # 论坛
    path('forum/list', forum.forum_list),
    path('forum/post/add', forum.post_add),
    path('forum/post/<int:post_id>', forum.post_detail),
    path('forum/post/<int:post_id>/comment', forum.comment_add),
    path('forum/post/<int:post_id>/delete', forum.post_delete),
    path('forum/comment/<int:comment_id>/delete', forum.comment_delete),
]
