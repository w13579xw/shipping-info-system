from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class M1(MiddlewareMixin):
    """ 中间件1 """

    def process_request(self, request):
        # 白名单列表
        except_lst = [
            # 登录认证相关
            '/admin/login',     # 管理员登录
            '/user/login',      # 用户登录
            '/user/logout',      # 用户退出
            '/user/register',   # 用户注册
            '/image/code',      # 验证码
            '/user/save_redirect_url',  # 保存重定向URL
            
            # 首页
            '/',                # 网站首页
            
            # 船舶识别相关
            '/ship/identify',  # 船舶识别接口
            '/ship/detect',    # 船舶检测接口
            
            # 问答系统相关
            '/qa',              # 问答系统首页
            '/qa/ask',          # 问答接口
            
            # 新闻资讯相关
            '/news/list',       # 新闻列表页
            '/news/api/list',   # 新闻列表API
            '/news/api/detail/', # 新闻详情API（支持任意news_id）
            
            # 论坛相关
            '/forum/list',            # 论坛首页
            '/forum/post/',            # 论坛评论
        ]
        
        # 检查是否需要认证
        need_auth = True
        for path in except_lst:
            # 如果路径以/结尾，使用startswith匹配
            if path.endswith('/') and path != '/':
                if request.path.startswith(path):
                    need_auth = False
                    break
            # 否则要求完全匹配
            else:
                if request.path == path:
                    need_auth = False
                    break
        
        print('需要认证：', need_auth)
        print('请求路径：', request.path)


        # 管理员路径列表
        admin_paths = [
            '/admin/',      # 管理员相关页面
            '/user/',       # 用户列表
            '/chart/',      # 数据统计
        ]

        # 检查是否需要管理员权限
        need_admin = False

        if need_auth:
            # 检查是否需要管理员权限
            for admin_path in admin_paths:
                if admin_path.endswith('/') and admin_path != '/':
                    if request.path.startswith(admin_path):
                        need_admin = True
                        break
                else:
                    if request.path == admin_path:
                        need_admin = True
                        break
            
            # 检查管理员session
            admin_info = request.session.get('admin_info')
            # 检查用户session
            user_info = request.session.get('user_info')
            
            # 需要管理员权限的路径
            if need_admin:
                if not admin_info:
                    # 保存当前URL用于登录后重定向
                    request.session['redirect_url'] = request.path
                    return redirect('/admin/login')
            # 其他需要认证的路径
            elif not user_info and not admin_info:
                # 保存当前URL用于登录后重定向
                request.session['redirect_url'] = request.path
                return redirect('/user/login')
        
        # 打印当前session信息
        print('当前管理员：', request.session.get('admin_info'))
        print('当前用户：', request.session.get('user_info'))
        print('需要管理员权限：', need_admin)
        print('最终路径：', request.session.get('redirect_url'))
        print('Session Key:', request.session.session_key)
        print(dict(request.session))

    def process_response(self, request, response):
        return response


class M3(MiddlewareMixin):
    """ 中间件3 """

    def process_request(self, request):
        print("中间件3：进来了")

    def process_response(self, request, response):
        print("中间价3：出去了")
        return response


class M2(MiddlewareMixin):
    """ 中间件2 """

    def process_request(self, request):
        print("中间件2：进来了")

    def process_response(self, request, response):
        print("中间价2：出去了")
        return response
