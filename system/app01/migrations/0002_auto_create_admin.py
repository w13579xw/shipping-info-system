from django.db import migrations
from app01.utils.encrypt import md5

def create_admin(apps, schema_editor):
    # 获取历史版本的模型类
    Admin = apps.get_model('app01', 'Admin')
    # 创建管理员账号
    if not Admin.objects.filter(username='Admin').exists():
        Admin.objects.create(username='Admin', password=md5('123'))

class Migration(migrations.Migration):
    dependencies = [
        ('app01', '0001_initial'),  # 依赖于初始迁移
    ]

    operations = [
        migrations.RunPython(create_admin),
    ]