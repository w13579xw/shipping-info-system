from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from app01.models import UserInfo
from app01.utils.form import UserModelForm
from app01.utils.encrypt import md5
from app01.utils.code import check_code


def user_lst(request):
    data_lst = UserInfo.objects.all()
    return render(request, 'user_list.html', {'data_lst': data_lst})


def user_add(request):
    if request.method == 'GET':
        print(request.method)
        form = UserModelForm()
        return render(request, 'user_add.html', {'form': form})
    # 用户POST提交数据,数据校验
    form = UserModelForm(data=request.POST)
    if form.is_valid():
        # 保存到数据库
        form.save()
        return redirect('/user/list')
    else:
        print('Error', form.errors)
    return render(request, 'user_add.html', {'form': form})


def user_edit(request, user_id):
    tar_user = UserInfo.objects.filter(id=user_id).first()
    # GET方法
    if request.method == 'GET':
        return render(request, 'user_edit.html', {'form': UserModelForm(instance=tar_user)})
    # POST方法
    form = UserModelForm(data=request.POST, instance=tar_user)
    if form.is_valid():
        # 如果用户输入了新密码，则更新密码
        if form.cleaned_data.get('password'):
            tar_user.password = form.cleaned_data.get('password')
            tar_user.save()
        else:
            form.save()
        return redirect('/user/list')
    # 如果有不合法内容仍留在此页面并打印提示信息
    return render(request, 'user_edit.html', {'form': form})


def user_del(request, user_id):
    UserInfo.objects.filter(id=user_id).delete()
    return redirect('/user/list')


def user_login(request):
    if request.method == 'GET':
        return render(request, 'user_login.html')
    
    username = request.POST.get('username')
    password = request.POST.get('password')
    code = request.POST.get('code')
    
    # 数据校验
    if not username or not password or not code:
        messages.error(request, '用户名、密码和验证码不能为空')
        return render(request, 'user_login.html')
    
    # 验证码校验
    session_code = request.session.get('image_code')
    if not session_code:
        messages.error(request, '验证码已过期，请刷新验证码')
        return render(request, 'user_login.html')
    
    if code.upper() != session_code.upper():
        messages.error(request, '验证码错误')
        return render(request, 'user_login.html')
    
    # 从数据库中查询用户
    user = UserInfo.objects.filter(username=username).first()
    if not user:
        messages.error(request, '用户名不存在')
        return render(request, 'user_login.html')
    
    # 验证密码
    if user.password != md5(password):  # 使用md5加密后比较密码
        messages.error(request, '密码错误')
        return render(request, 'user_login.html')
    
    # 清除可能存在的管理员session
    if 'admin_info' in request.session:
        del request.session['admin_info']
    
    # 登录成功，将用户信息和类型保存到session
    request.session['user_info'] = {
        'id': user.id,
        'username': user.username,
        'type': 'user'  # 标识为普通用户
    }
    # 设置session过期时间为30分钟
    request.session.set_expiry(60 * 30)
    
    # 检查是否有重定向URL
    redirect_url = request.session.get('redirect_url')
    if redirect_url:
        del request.session['redirect_url']
        return redirect(redirect_url)
    return redirect('/')

def save_redirect_url(request):
    """保存重定向URL到session"""
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        redirect_url = data.get('redirect_url')
        if redirect_url:
            request.session['redirect_url'] = redirect_url
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': '不支持的请求方法'})



def user_logout(request):
    # 清除特定的session键
    if 'user_info' in request.session:
        del request.session['user_info']
    if 'info' in request.session:
        del request.session['info']
    if 'image_code' in request.session:
        del request.session['image_code']
    # 完全清除session
    request.session.flush()
    response = redirect('/')
    # 添加页面刷新的响应头
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def image_code(request):
    img, code_str = check_code()
    request.session['image_code'] = code_str
    request.session.set_expiry(60)
    response = HttpResponse(content_type='png')
    img.save(response, 'png')
    print('code:', code_str)
    return response
