from django.http import JsonResponse
from django.shortcuts import render
from datetime import datetime, timedelta
from app01.models import ModuleVisit
from django.db.models import Count
from django.db.models.functions import ExtractHour

def chart_list(request):
    return render(request, 'chart_list.html')

def module_line(request):
    # 获取最近7天的日期
    end_date = datetime.now().replace(hour=23, minute=59, second=59)
    start_date = (end_date - timedelta(days=6)).replace(hour=0, minute=0, second=0)
    dates = [(start_date + timedelta(days=i)).strftime('%m-%d') for i in range(7)]
    
    # 从数据库获取各模块的访问数据
    module_data = {}
    for module_code, module_name in ModuleVisit.MODULE_CHOICES:
        module_data[module_name] = {'name': module_name, 'type': 'line', 'data': []}
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            next_date = current_date + timedelta(days=1)
            count = ModuleVisit.objects.filter(
                module_name=module_code,
                visit_time__gte=current_date,
                visit_time__lt=next_date
            ).count()
            module_data[module_name]['data'].append(count)
    
    series = list(module_data.values())
    
    return JsonResponse({
        'status': True,
        'xAxis': dates,
        'series': series
    }, json_dumps_params={'ensure_ascii': False})

def module_pie(request):
    # 从数据库获取各模块的总访问量数据
    series = []
    for module_code, module_name in ModuleVisit.MODULE_CHOICES:
        count = ModuleVisit.objects.filter(module_name=module_code).count()
        series.append({'value': count, 'name': module_name})
    
    return JsonResponse({
        'status': True,
        'series': series
    }, json_dumps_params={'ensure_ascii': False})

def user_bar(request):
    # 获取管理员和用户数量统计
    from app01.models import Admin, UserInfo
    
    admin_count = Admin.objects.count()
    user_count = UserInfo.objects.count()
    
    series = [{
        'name': '用户类型',
        'type': 'bar',
        'data': [
            {'name': '管理员', 'value': admin_count, 'itemStyle': {'color': '#FF6B6B'}},
            {'name': '普通用户', 'value': user_count, 'itemStyle': {'color': '#4ECDC4'}}
        ]
    }]
    
    return JsonResponse({
        'status': True,
        'xAxis': ['管理员', '普通用户'],
        'series': series
    }, json_dumps_params={'ensure_ascii': False})


def activity_stack(request):
    # 用户活跃度时段分布数据
    hours = [f'{i:02d}:00' for i in range(24)]
    
    # 获取最近30天的数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # 工作日数据统计
    workday_data = ModuleVisit.objects.filter(
        visit_time__gte=start_date,
        visit_time__lte=end_date,
        visit_time__week_day__in=[2, 3, 4, 5, 6]  # 周一到周五
    ).annotate(
        hour=ExtractHour('visit_time')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # 周末数据统计
    weekend_data = ModuleVisit.objects.filter(
        visit_time__gte=start_date,
        visit_time__lte=end_date,
        visit_time__week_day__in=[1, 7]  # 周六和周日
    ).annotate(
        hour=ExtractHour('visit_time')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # 初始化24小时的数据列表
    workday_counts = [0] * 24
    weekend_counts = [0] * 24
    
    # 填充工作日数据
    for item in workday_data:
        workday_counts[item['hour']] = item['count']
    
    # 填充周末数据
    for item in weekend_data:
        weekend_counts[item['hour']] = item['count']
    
    series = [
        {
            'name': '工作日',
            'type': 'bar',
            'stack': 'total',
            'data': workday_counts
        },
        {
            'name': '周末',
            'type': 'bar',
            'stack': 'total',
            'data': weekend_counts
        }
    ]
    
    return JsonResponse({
        'status': True,
        'xAxis': hours,
        'series': series
    }, json_dumps_params={'ensure_ascii': False})