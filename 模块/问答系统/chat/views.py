from django.shortcuts import render
from openai import OpenAI
import os
from django.conf import settings
import logging

# 配置日志记录
logger = logging.getLogger(__name__)

def get_ai_response(messages):
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )

    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        return {
            'content': completion.choices[0].message.content,
            'reasoning': getattr(completion.choices[0].message, 'reasoning_content', '')
        }
    except Exception as e:
        logger.error(f"AI响应出错: {str(e)}")
        return {
            'content': f"很抱歉，服务出现了一些问题，请稍后再试。",
            'reasoning': ''
        }

def chat_view(request):
    if 'messages' not in request.session:
        request.session['messages'] = []

    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()
        if user_message:
            try:
                # 添加用户消息到会话
                request.session['messages'].append({'role': 'user', 'content': user_message})

                # 获取AI响应
                response = get_ai_response(request.session['messages'])

                # 添加AI响应到会话
                request.session['messages'].append({
                    'role': 'assistant',
                    'content': response['content'],
                    'reasoning': response['reasoning']
                })

                request.session.modified = True
            except Exception as e:
                logger.error(f"聊天视图处理出错: {str(e)}")
                return render(request, 'chat.html', {
                    'messages': request.session['messages'],
                    'error': '处理您的请求时出现错误，请稍后重试。'
                })

    return render(request, 'chat.html', {
        'messages': request.session['messages']
    })