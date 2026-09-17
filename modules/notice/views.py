"""站内消息提醒：列表 / 未读数 / 标记已读。

消息属于「用户自身的数据」，与个人资料、心情同类，不登记 PERMISSION_PATH_MAP；
所有查询与更新都带 recipient 限定，任何人只能看到并操作自己的消息。
"""

from django.utils import timezone
from django.views.decorators.http import require_POST

from modules.comment.serializers.comment import build_user_map
from modules.comment.service.comment import is_valid_uuid
from modules.notice.models import Notice
from modules.notice.serializers.notice import (
    build_article_title_map,
    build_comment_map,
    format_notice,
)
from modules.notice.service.notice import get_unread_count
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import limit_queryset, post_handle


def filter_read_status(sql, params):
    """已读筛选：不传表示全部，传 true / false 表示只看已读 / 未读"""
    is_read = params.get('isRead')
    if is_read is None or is_read == '':
        return sql
    return sql.filter(isRead=str(is_read).lower() in ('true', '1'))


@require_POST
def get_notice_list(request):
    """
    消息列表：最新在前，可按已读状态筛选。

    固定查询次数：通知分页 + 触发的评论（含被回复的顶层评论）+ 用户 + 文章标题，
    不逐条查库。
    """
    params = post_handle(request)
    notice_sql = filter_read_status(
        Notice.objects.filter(recipient=get_user_id(request)), params)

    page_data = limit_queryset(params, notice_sql)
    notice_list = list(page_data['result'])
    if not notice_list:
        return res_search({'total': page_data['total'], 'result': []})

    comment_map = build_comment_map(notice_list)
    user_map = build_user_map({notice.sender for notice in notice_list})
    title_map = build_article_title_map(
        notice.targetId for notice in notice_list if notice.targetType == 'article')

    return res_search({
        'total': page_data['total'],
        'result': [
            format_notice(notice, user_map, comment_map, title_map)
            for notice in notice_list
        ],
    })


@require_POST
def get_notice_unread_count(request):
    """未读数：顶部角标轮询用"""
    return res_search({'count': get_unread_count(get_user_id(request))})


@require_POST
def read_notice(request):
    """标记指定消息已读；已读的不重复覆盖 readTime"""
    params = post_handle(request)
    notice_ids = params.get('ids') or []
    if not isinstance(notice_ids, list):
        return res_handle(501, '参数格式不正确', None)
    valid_ids = [item for item in notice_ids if is_valid_uuid(item)]
    if not valid_ids:
        return res_handle(501, '请选择要标记的消息', None)
    Notice.objects.filter(
        recipient=get_user_id(request), id__in=valid_ids, isRead=False
    ).update(isRead=True, readTime=timezone.now())
    return res_handle(0, '操作成功', True)


@require_POST
def read_all_notice(request):
    """全部已读"""
    Notice.objects.filter(
        recipient=get_user_id(request), isRead=False
    ).update(isRead=True, readTime=timezone.now())
    return res_handle(0, '操作成功', True)
