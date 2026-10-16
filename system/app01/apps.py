from django.apps import AppConfig
from app01.utils.encrypt import md5


class App01Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app01'

    def ready(self):
        # try:
        #     from .models import Admin
        #     if not Admin.objects.filter(username='Admin').exists():
        #         Admin.objects.create(username='Admin',
        #                            password=md5('123'))
        #         print('管理员账号Admin创建成功')
        #     print('python manage.py makemigrations 或 python manage.py migrate 执行成功')
        # except Exception as e:
        #     print('报错问题是：', e)
        #     print('@@@@@出现此提示无需惊慌')
        #     print('@@@@@如果你正在执行python manage.py makemigrations,则忽略此信息')
        #     print('@@@@@如果你正在执行python manage.py migrate, 请你再次执行此命令')
        #     print('@@@@@执行完上述指令后最终执行python manage.py runserver 8080')
        #     print('@@@@@即可成功运行项目(账号Admin,密码123)')
        # 管理员账号的创建已移至数据迁移文件中处理
        pass
