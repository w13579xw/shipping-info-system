from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.contrib import messages

from app01.models import UserInfo
from app01.utils.encrypt import md5


class RegisterForm(forms.Form):
    username = forms.CharField(
        label='用户名',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入用户名', 'data-empty-message': '这个字段是必填项'}),
        required=True
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请输入密码', 'data-empty-message': '这个字段是必填项'}, render_value=True),
        required=True
    )
    confirm_password = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '请确认密码', 'data-empty-message': '这个字段是必填项'}, render_value=True),
        required=True
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if UserInfo.objects.filter(username=username).exists():
            raise ValidationError('用户名已存在')
        return username

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm = self.cleaned_data.get('confirm_password')
        if pwd != confirm:
            raise ValidationError('两次密码不一致')
        return confirm


def register(request):
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    form = RegisterForm(data=request.POST)
    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = md5(form.cleaned_data.get('password'))
        UserInfo.objects.create(username=username, password=password)
        messages.success(request, '注册成功')
        return redirect('/user/login')
    return render(request, 'register.html', {'form': form})