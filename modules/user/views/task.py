import datetime

from django.db.models.functions import TruncMonth, TruncDate
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from modules.user.models import UserTask
from modules.user.serializers.task import UserTaskSerializers
from modules.user.service.task import validate_add_task_params
from modules.user.service.user import add_user_activity
from django.db.models import Q, Sum, F
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import post_handle, limit_queryset, obj_has_attr


@require_POST
def get_user_task_list(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    sql = UserTask.objects.all().filter(user=user_id)
    if obj_has_attr(params, 'status'):
        sql = sql.filter(status=params['status'])
    if obj_has_attr(params, 'priority'):
        sql = sql.filter(priority=params['priority'])
    if obj_has_attr(params, 'startTime') and obj_has_attr(params, 'endTime'):
        sql = sql.filter(deadline__range=(params['startTime'], params['endTime']))
    # 按结束时间排序，默认倒序
    sort_order = params.get('sortOrder') or 'descending'
    order_prefix = '-' if sort_order == 'descending' else ''
    sql = sql.order_by(f'{order_prefix}endTime')
    queryset_data = limit_queryset(params, sql)
    data = UserTaskSerializers(instance=queryset_data['result'], many=True)
    return res_search({'result': data.data, 'total': queryset_data['total']})


@require_POST
def get_user_task_panel_list(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    sql = UserTask.objects.all().filter(user=user_id).filter(
        Q(endTime__range=(params['startTime'], params['endTime'])) | Q(status='pending') | Q(status='todo'))

    data = UserTaskSerializers(instance=sql, many=True)
    return res_search(data.data)


@require_POST
def get_user_task_remind_list(request):
    user_id = get_user_id(request)
    sql = (UserTask.objects.all().filter(user=user_id)
           .filter(status__in=['todo', 'pending'])
           .filter(deadline__isnull=False)
           .order_by('deadline'))
    data = UserTaskSerializers(instance=sql, many=True)
    return res_search(data.data)


@require_POST
def get_user__recent_task_list(request):
    user_id = get_user_id(request)
    sql = UserTask.objects.all().filter(user=user_id).filter(status='done').order_by('-endTime')[:10]
    data = UserTaskSerializers(instance=sql, many=True)
    return res_search(data.data)


@require_POST
def add_user_task(request):
    params = post_handle(request)
    params['tags'] = ','.join(params['tags'])
    msg = validate_add_task_params(params)
    if msg:
        return res_handle(501, msg, False)
    params['user'] = get_user_id(request)
    task = UserTask.objects.create(**params)
    # 仅「待办/进行中」记录创建动态；直接记为已完成（补录历史）不产生动态
    if params['status'] in ('todo', 'pending'):
        add_user_activity(request, 'create_task', task.id, '创建事项', {'title': params['title']})
    return res_handle(0, '添加成功', True)


@require_POST
def edit_user_task(request):
    params = post_handle(request)
    params['tags'] = ','.join(params['tags'])
    msg = validate_add_task_params(params)
    if msg:
        return res_handle(501, msg, False)
    task = UserTask.objects.filter(id=params['id']).first()
    was_done = task.status == 'done' if task else False
    UserTask.objects.filter(id=params['id']).update(**params)
    if not was_done and params['status'] == 'done':
        add_user_activity(request, 'complete_task', params['id'], '完成任务', {'title': params['title']})
    return res_handle(0, '修改成功', True)


@require_POST
def delete_user_task(request):
    params = post_handle(request)
    UserTask.objects.filter(id__in=params['ids']).delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_person_score_stats(request):
    params = post_handle(request)
    user = get_user_id(request)

    # 前端传参（JSON body）
    range_type = params["rangeType"]  # week | month | year
    start_date = params["startDate"]
    end_date = params["endDate"]

    today = datetime.date.today()

    # 如果没传日期，就根据 range_type 自动计算
    if not start_date or not end_date:
        if range_type == "week":
            start_date = today - datetime.timedelta(days=6)
        elif range_type == "month":
            start_date = today - datetime.timedelta(days=29)
        elif range_type == "year":
            start_date = today.replace(year=today.year - 1)
        else:
            return res_handle(500, '请传入日期范围或有效的 rangeType', True)
        end_date = today
    else:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

    delta_days = (end_date - start_date).days
    if delta_days > 31:
        trunc_func = TruncMonth
        date_format = "%Y-%m"
        step = "month"
    else:
        trunc_func = TruncDate
        date_format = "%Y-%m-%d"
        step = "day"

    # ORM 聚合
    qs = (
        UserTask.objects.filter(
            user=user,
            endTime__date__gte=datetime.datetime.combine(start_date, datetime.time.min),
            endTime__date__lte=datetime.datetime.combine(end_date, datetime.time.max),
        )
        .annotate(period=trunc_func("endTime"))
        .values("period")
        .annotate(total_score=Sum((F("importance") * 0.7 +
                                   F("urgency") * 0.3) * (
                                   F("growth") * 0.7 +
                                   F("happiness") * 0.3 -
                                   F("negative") * 1.0)))
        .order_by("period")
    )

    score_map = {}
    if step == "day":
        for q in qs:
            # key: (year, month, day)
            score_map[(q["period"].year, q["period"].month, q["period"].day)] = q["total_score"]
    else:  # 按月
        for q in qs:
            # key: (year, month)
            score_map[(q["period"].year, q["period"].month)] = q["total_score"]

    # 补齐区间
    result = []
    current = start_date
    if step == "day":
        while current <= end_date:
            key = (current.year, current.month, current.day)
            score = round(score_map.get(key, 0) or 0, 2)
            result.append({"date": current.strftime(date_format), "score": score})
            current += datetime.timedelta(days=1)
    else:
        while current <= end_date:
            key = (current.year, current.month)
            score = round(score_map.get(key, 0) or 0, 2)
            result.append({"date": current.strftime(date_format), "score": score})
            # 下个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)
    return res_search(result)
