from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render, redirect

from app01.models import Admin, UserInfo
from app01.utils.code import check_code
from app01.utils.encrypt import md5
from django.contrib import messages


class LoginForm(forms.Form):
    username = forms.CharField(
        label='用户名',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入用户名', 'data-empty-message': '这个字段是必填项'}),
        required=True,  # 默认值不为空
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请输入密码', 'data-empty-message': '这个字段是必填项'}, render_value=True),
        required=True,  # 默认值不为空
    )

    def clean_password(self):
        user = self.cleaned_data.get('username')
        pwd_md5 = md5(self.cleaned_data.get('password'))
        if not Admin.objects.filter(username=user, password=pwd_md5).exists():
            raise ValidationError('账号或密码错误')
        return pwd_md5


def login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'admin_login.html', {'form': form})
    form = LoginForm(data=request.POST)
    if form.is_valid():
        username = form.cleaned_data.get('username')
        u_id = Admin.objects.filter(username=username).first().id
        # 清除可能存在的用户session
        if 'user_info' in request.session:
            del request.session['user_info']
        # 设置管理员session
        request.session['admin_info'] = {
            'id': u_id,
            'username': username,
            'type': 'admin'  # 标识为管理员用户
        }
        # 登录有限时限30分钟/30分钟自动退出
        request.session.set_expiry(60 * 30)
        # 检查是否有重定向URL
        redirect_url = request.session.get('redirect_url')
        if redirect_url:
            del request.session['redirect_url']
            return redirect(redirect_url)
        return redirect('/chart/list')
    return render(request, 'admin_login.html', {'form': form})


def logout(request):
    # 清除特定的session键
    if 'admin_info' in request.session:
        del request.session['admin_info']
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

