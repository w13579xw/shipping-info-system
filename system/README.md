# 航运信息系统项目说明

## 项目目录结构

### 根目录
- `manage.py`: Django项目的命令行工具，用于项目管理
- `db.sqlite3`: SQLite数据库文件
- `README.md`: 项目说明文档

### myProject目录（项目配置）
- `settings.py`: 项目的主要配置文件
- `urls.py`: 项目的URL路由配置
- `wsgi.py`: WSGI应用配置文件
- `asgi.py`: ASGI应用配置文件

### app01目录（主应用）

#### 核心文件
- `models.py`: 数据模型定义
- `admin.py`: Django管理后台配置
- `apps.py`: 应用配置文件
- `tests.py`: 测试文件

#### views目录（视图函数）
- `account.py`: 账户相关视图
- `admin.py`: 管理员相关视图
- `chart.py`: 数据图表相关视图
- `forum.py`: 论坛相关视图
- `index.py`: 首页相关视图
- `news.py`: 新闻相关视图
- `qa.py`: 问答相关视图
- `register.py`: 注册相关视图
- `ship.py`: 船舶相关视图
- `user.py`: 用户相关视图

#### templates目录（模板文件）
- `layout.html`: 基础布局模板
- `index.html`: 首页模板
- `admin_login.html`: 管理员登录页面
- `admin_list.html`: 管理员列表页面
- `admin_add.html`: 添加管理员页面
- `admin_edit.html`: 编辑管理员页面
- `user_login.html`: 用户登录页面
- `user_list.html`: 用户列表页面
- `user_add.html`: 添加用户页面
- `user_edit.html`: 编辑用户页面
- `chart_list.html`: 图表展示页面
- `news_list.html`: 新闻列表页面
- `news_recommended.html`: 推荐新闻页面
- `qa.html`: 问答页面
- `register.html`: 注册页面
- `ship_identify.html`: 船舶识别页面

#### static目录（静态文件）
- `css/`: CSS样式文件
- `favicon/`: 网站图标
- `img/`: 图片资源
- `models/`: 模型文件
  - `ship_detection.pt`: 船舶检测模型

#### utils目录（工具类）
- `bm25.py`: BM25搜索算法实现
- `build_kg_utils.py`: 知识图谱构建工具
- `code.py`: 验证码相关工具
- `detect_language.py`: 语言检测工具
- `encrypt.py`: 加密工具
- `form.py`: 表单处理工具
- `pagination.py`: 分页工具
- `stopwords.py`: 停用词处理

#### middleware目录（中间件）
- `auth.py`: 认证中间件

#### migrations目录（数据库迁移）
- `0001_initial.py`: 初始数据库迁移
- `0002_auto_create_admin.py`: 创建管理员迁移
- `0003_newshistory.py`: 新闻历史迁移

### media目录（媒体文件）
- `ship_detection/`: 船舶检测相关媒体文件

### md_pic目录（文档图片）
包含各种系统界面截图，用于文档说明

## 功能模块说明

1. 用户管理：用户的注册、登录、信息管理
2. 管理员系统：管理员账户管理和权限控制
3. 新闻系统：新闻的展示和推荐
4. 问答系统：用户问答功能
5. 船舶识别：基于深度学习的船舶检测功能
6. 数据可视化：使用图表展示各类数据
7. 论坛系统：用户交流平台

