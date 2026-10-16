from django.db import models


# Create your models here.

class Admin(models.Model):
    """ 管理员 """
    username = models.CharField(verbose_name='用户名', max_length=32)
    password = models.CharField(verbose_name='密码', max_length=64)

    def __str__(self):
        return self.username


# class Department(models.Model):
#     """部门表"""
#     title = models.CharField(max_length=32, verbose_name='标题')

#     def __str__(self):
#         return self.title


class UserInfo(models.Model):
    """用户表"""
    username = models.CharField(verbose_name='用户名', max_length=32)
    password = models.CharField(verbose_name='密码', max_length=64)

    def __str__(self):
        return self.username


# class PrettyNumber(models.Model):
#     """ 靓号表 """
#     mobile = models.CharField(verbose_name='手机号', max_length=11)
#     price = models.SmallIntegerField(verbose_name='价格', default=0, null=True, blank=True)
#     level_choices = (
#         (1, '1级'),
#         (2, '2级'),
#         (3, '3级')
#     )
#     level = models.SmallIntegerField(verbose_name='级别', choices=level_choices, default=1)
#     status_choices = (
#         (1, '已占用'),
#         (2, '未使用')
#     )
#     status = models.SmallIntegerField(verbose_name='状态', choices=status_choices, default=2)


# class Task(models.Model):
#     level_choices = (
#         (1, '紧急'),
#         (2, '重要'),
#         (3, '临时')
#     )
#     level = models.SmallIntegerField(verbose_name='级别', choices=level_choices, default=1)
#     title = models.CharField(verbose_name='标题', max_length=32)
#     detail = models.TextField(verbose_name='详细信息')
#     manager = models.ForeignKey(to=Admin, verbose_name='负责人', on_delete=models.CASCADE)


# class Order(models.Model):
#     oid = models.CharField(verbose_name='订单号', max_length=64)
#     title = models.CharField(verbose_name='名称', max_length=32)
#     price = models.IntegerField(verbose_name='价格')
#     status_choice = (
#         (1, '待支付'),
#         (2, '已支付'),
#     )
#     status = models.SmallIntegerField(verbose_name='状态', choices=status_choice, default=1)
#     admin = models.ForeignKey(verbose_name='管理员', to='Admin', on_delete=models.CASCADE)


# class Boss(models.Model):
#     name = models.CharField(verbose_name='老板', max_length=32)
#     age = models.IntegerField(verbose_name='年龄')
#     img = models.CharField(verbose_name='图片', max_length=64)


# class City(models.Model):
#     name = models.CharField(verbose_name='城市', max_length=32)
#     count = models.IntegerField(verbose_name='人口')
#     # 本质上也是CharField，自动保存
#     img = models.FileField(verbose_name='LOGO', max_length=128, upload_to='city2')


class Post(models.Model):
    """论坛帖子表"""
    title = models.CharField(verbose_name='标题', max_length=100)
    content = models.TextField(verbose_name='内容')
    author = models.ForeignKey(UserInfo, verbose_name='作者', on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新时间', auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Comment(models.Model):
    """评论表"""
    post = models.ForeignKey(Post, verbose_name='帖子', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(verbose_name='内容')
    author = models.ForeignKey(UserInfo, verbose_name='作者', on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username}的评论'


class ModuleVisit(models.Model):
    """模块访问记录表"""
    MODULE_CHOICES = (
        ('knowledge_graph', '知识图谱'),
        ('ship_identify', '船舶识别'),
        ('news_query', '资讯查询'),
        ('forum', '发言论坛')
    )
    
    module_name = models.CharField(verbose_name='模块名称', max_length=32, choices=MODULE_CHOICES)
    user = models.ForeignKey(UserInfo, verbose_name='访问用户', on_delete=models.CASCADE, null=True, blank=True)
    visit_time = models.DateTimeField(verbose_name='访问时间', auto_now_add=True)
    
    class Meta:
        ordering = ['-visit_time']
        
    def __str__(self):
        return f'{self.user.username if self.user else "游客"}访问{self.get_module_name_display()}'


class NewsHistory(models.Model):
    """新闻浏览历史表"""
    user = models.ForeignKey(UserInfo, verbose_name='用户', on_delete=models.CASCADE)
    news_id = models.CharField(verbose_name='新闻ID', max_length=64)
    title = models.CharField(verbose_name='新闻标题', max_length=255)
    view_time = models.DateTimeField(verbose_name='浏览时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '新闻浏览历史'
        verbose_name_plural = '新闻浏览历史'
        ordering = ['-view_time']
        
    def __str__(self):
        return f'{self.user.username}浏览{self.title}'
