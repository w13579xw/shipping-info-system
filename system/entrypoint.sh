#!/bin/sh
set -e

# 启动前自动执行数据库迁移
python manage.py migrate --noinput

# 使用 gunicorn 运行（生产可用）
exec gunicorn myProject.wsgi:application --bind 0.0.0.0:8000
