import datetime
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date


def get_count_stats(
        queryset,  # 已经过滤好条件的 queryset
        date_field: str,  # 日期字段名，例如 "createTime"
        range_type: str,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
):
    today = datetime.date.today()

    # 如果没传日期，就根据 range_type 自动计算
    if not start_date or not end_date:
        if range_type == "week":
            start_date = today - datetime.timedelta(days=6)
        elif range_type == "month":
            start_date = today - datetime.timedelta(days=29)
        elif range_type == "year":
            start_date = today.replace(year=today.year - 1)
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
        queryset.annotate(period=trunc_func(date_field))
        .values("period")
        .annotate(total_count=Count("id"))
        .order_by("period")
    )

    # 构建字典
    count_map = {}
    if step == "day":
        for q in qs:
            key = (q["period"].year, q["period"].month, q["period"].day)
            count_map[key] = q["total_count"]
    else:
        for q in qs:
            key = (q["period"].year, q["period"].month)
            count_map[key] = q["total_count"]

    result = []
    current = start_date
    if step == "day":
        while current <= end_date:
            key = (current.year, current.month, current.day)
            result.append({
                "date": current.strftime(date_format),
                "count": count_map.get(key, 0)
            })
            current += datetime.timedelta(days=1)
    else:
        while current <= end_date:
            key = (current.year, current.month)
            result.append({
                "date": current.strftime(date_format),
                "count": count_map.get(key, 0)
            })
            # 下个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

    return result


def get_month_stats(queryset):
    data_count = queryset.count()
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    if this_month_start.month == 12:
        next_month_start = this_month_start.replace(year=this_month_start.year + 1, month=1, day=1)
    else:
        next_month_start = this_month_start.replace(month=this_month_start.month + 1, day=1)
    if this_month_start.month == 1:
        last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12, day=1)
    else:
        last_month_start = this_month_start.replace(month=this_month_start.month - 1, day=1)

    this_month_count = queryset.filter(
        createTime__gte=this_month_start,
        createTime__lt=next_month_start,
    ).count()

    last_month_count = queryset.filter(
        createTime__gte=last_month_start,
        createTime__lt=this_month_start,

    ).count()

    result = {
        'count': data_count,
        "this": this_month_count,
        "last": last_month_count,
        "diff": this_month_count - last_month_count
    }

    return result


def get_week_stats(queryset):
    data_count = queryset.count()
    today = timezone.now().date()
    # 本周一
    this_week_start = today - datetime.timedelta(days=today.weekday())
    # 下周一
    next_week_start = this_week_start + datetime.timedelta(days=7)
    # 上周一
    last_week_start = this_week_start - datetime.timedelta(days=7)

    # 这周的文章数量
    this_week_count = queryset.filter(
        createTime__gte=this_week_start,
        createTime__lt=next_week_start
    ).count()

    # 上周的文章数量
    last_week_count = queryset.filter(
        createTime__gte=last_week_start,
        createTime__lt=this_week_start
    ).count()

    # 差值
    diff = this_week_count - last_week_count

    result = {
        'count': data_count,
        "this": this_week_count,
        "last": last_week_count,
        "diff": diff
    }

    return result


def get_current_stat(queryset):
    now = datetime.datetime.now()
    start_of_week = now - datetime.timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + datetime.timedelta(days=7)

    year_count = queryset.filter(createTime__year=now.year).count()
    month_count = queryset.filter(createTime__year=now.year,
                                  createTime__month=now.month).count()
    week_count = queryset.filter(
        createTime__gte=start_of_week,
        createTime__lt=end_of_week
    ).count()

    data = {
        "year": year_count,
        "month": month_count,
        "week": week_count
    }
    return data
