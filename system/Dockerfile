# 航运信息系统 - Django 应用镜像
FROM python:3.11-slim

# 阻止生成 .pyc、强制日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 系统级依赖（mysqlclient / opencv / Pillow 编译与运行所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        pkg-config \
        default-libmysqlclient-dev \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 先安装依赖，充分利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目代码
COPY . .

# 收集静态文件到 STATIC_ROOT（供 whitenoise 服务）
RUN python manage.py collectstatic --noinput

# 迁移 + 启动入口
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
