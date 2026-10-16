from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import cv2
import numpy as np
from pathlib import Path
import os
import json
from ultralytics import YOLO
from django.conf import settings
import shutil

# 船舶类别映射字典
SHIP_CLASS_MAP = {
    'Cargo': '货船',
    'Carrier': '航空母舰',
    'Cruise': '邮轮',
    'Tanker': '油轮',
    'Warship': '军舰'
}

# 船舶类别概述信息
SHIP_CLASS_DESC = {
    'Cargo': '主要用于运输货物的商船，包括散货船、集装箱船等。',
    'Carrier': '主要用于搭载飞机、执行军事任务的军舰。',
    'Cruise': '主要用于旅游的客船，通常外观豪华，适合远洋旅行。',
    'Tanker': '用于运输液体货物（如原油、化学品、液化天然气等）的船舶。',
    'Warship': '主要用于军事用途，包括驱逐舰、护卫舰、潜艇等。'
}

# 获取models目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = os.path.join(BASE_DIR, 'static', 'models', 'ship_detection.pt')

def identify(request):
    # 记录模块访问
    from app01.models import ModuleVisit, UserInfo
    user = None
    if request.session.get('user_info'):
        user = UserInfo.objects.get(id=request.session['user_info']['id'])
    ModuleVisit.objects.create(module_name='ship_identify', user=user)
    return render(request, 'ship_identify.html')


@csrf_exempt
def save_image(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        data = json.loads(request.body)
        image_url = data.get('image_url')
        if not image_url:
            return JsonResponse({'success': False, 'error': '未提供图片URL'})

        # 从data URL中提取图片数据
        if image_url.startswith('data:image/'):
            # 处理Base64编码的图片数据
            import base64
            try:
                # 分离metadata和base64数据
                header, encoded = image_url.split(',', 1)
                # 解码base64数据
                image_data = base64.b64decode(encoded)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'无效的图片数据：{str(e)}'})

            # 从header中获取文件扩展名
            import re
            mime_match = re.search('data:image/([a-zA-Z]+);base64', header)
            if mime_match:
                file_ext = '.' + mime_match.group(1)
            else:
                file_ext = '.jpg'  # 默认扩展名
        else:
            # 从URL中提取相对路径
            image_path = image_url.split('?')[0]  # 移除URL参数
            if image_path.startswith('/'):
                image_path = image_path[1:]  # 移除开头的斜杠

            # 构建源文件的完整路径
            source_path = os.path.join(settings.BASE_DIR, image_path)
            
            if not os.path.exists(source_path):
                return JsonResponse({'success': False, 'error': '图片文件不存在'})

            # 获取文件扩展名
            file_ext = os.path.splitext(source_path)[1]

        # 生成目标文件名（使用时间戳和UUID确保唯一性）
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        save_filename = f'saved_image_{timestamp}_{unique_id}{file_ext}'

        # 确保目标目录存在
        save_dir = os.path.join(settings.MEDIA_ROOT, 'ship_detection')
        os.makedirs(save_dir, exist_ok=True)

        # 构建目标文件的完整路径
        save_path = os.path.join(save_dir, save_filename)

        # 保存文件
        if image_url.startswith('data:image/'):
            with open(save_path, 'wb') as f:
                f.write(image_data)
        else:
            import shutil
            shutil.copy2(source_path, save_path)

        return JsonResponse({
            'success': True,
            'message': '图片保存成功',
            'saved_path': os.path.join('media', 'ship_detection', save_filename)
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'保存图片时出错：{str(e)}'})

@csrf_exempt
def detect_ship(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        # 获取上传的图片
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'success': False, 'error': '未找到上传的图片'})

        # 保存上传的图片
        save_dir = os.path.join(settings.MEDIA_ROOT, 'ship_detection')
        print(f'保存目录: {save_dir}')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            print('创建保存目录成功')

        # 生成临时文件路径
        import uuid
        file_ext = os.path.splitext(image_file.name)[1]
        temp_filename = f"{uuid.uuid4().hex}{file_ext}"
        temp_path = os.path.join(save_dir, temp_filename)

        # 保存上传的文件
        print(f'临时文件路径: {temp_path}')
        with open(temp_path, 'wb+') as f:
            for chunk in image_file.chunks():
                f.write(chunk)
        print('上传文件保存成功')

        # 加载模型并进行预测
        try:
            print(f'加载模型路径: {MODEL_PATH}')
            model = YOLO(MODEL_PATH)
            print('模型加载成功，开始预测...')
            results = model.predict(source=temp_path, save=True, project=save_dir)
            print('模型预测完成')
            
            if not results:
                return JsonResponse({'success': False, 'error': '模型未返回有效结果'})

            # 获取结果图片路径
            predict_dir = os.path.join(save_dir, 'predict')
            result_filename = temp_filename
            predict_path = os.path.join(predict_dir, temp_filename)
            final_path = os.path.join(save_dir, result_filename)

            # 移动结果图片到目标目录
            print(f'预测结果路径: {predict_path}')
            print(f'最终保存路径: {final_path}')
            try:
                if os.path.exists(predict_path):
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    # 如果目标文件已存在，先删除
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    shutil.copy2(predict_path, final_path)
                    print('结果图片复制成功')
                    
                    # 验证文件是否成功复制
                    if not os.path.exists(final_path):
                        return JsonResponse({'success': False, 'error': '结果图片复制失败'})
                else:
                    print('预测结果图片不存在')
                    return JsonResponse({'success': False, 'error': '模型预测结果图片未生成'})

                # 删除predict文件夹
                if os.path.exists(predict_dir):
                    shutil.rmtree(predict_dir)
                    print('清理predict文件夹')

                # 删除识别结果文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print('识别结果文件删除成功')


            except Exception as e:
                print(f'文件处理出错：{str(e)}')
                return JsonResponse({'success': False, 'error': f'文件处理出错：{str(e)}'})

            # 处理检测结果
            detections = []
            if len(results) > 0:
                boxes = results[0].boxes
                print(f'检测到 {len(boxes)} 个目标')
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = results[0].names[cls]
                    detections.append({
                        'class': class_name,
                        'class_zh': SHIP_CLASS_MAP.get(class_name, class_name),
                        'description': SHIP_CLASS_DESC.get(class_name, ''),
                        'confidence': conf
                    })
                    print(f'类别：{results[0].names[cls]}, 置信度：{conf:.2f}, 边界框：[{x1}, {y1}, {x2}, {y2}]')

            result_path = os.path.join('media', 'ship_detection', result_filename)
            result_path = result_path.replace('\\', '/')
            return JsonResponse({
                'success': True,
                'result_image': result_path,
                'detections': detections
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'模型处理失败：{str(e)}'})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'处理过程中出错：{str(e)}'
        })