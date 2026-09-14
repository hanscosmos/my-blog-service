from django.views.decorators.http import require_POST

from modules.article.models import Article
from modules.comment.models import Comment
from modules.comment.serializers.comment import build_user_map, format_flat_comment, format_root_comment
from modules.comment.service.comment import (
    COMMENT_TARGET_TYPES,
    can_delete_comment,
    get_target_author_id,
    is_valid_uuid,
    validate_add_comment_params,
)
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import limit_queryset, post_handle


def get_visible_comments():
    """前台可见评论：未删除 + 状态为 visible（先发后审，被隐藏的不展示）"""
    return Comment.objects.filter(isDelete=False, status='visible')


def filter_target_comments(sql, target_type, target_id):
    """限定到某个评论对象（文章 id / 留言板）"""
    return sql.filter(targetType=target_type, targetId=target_id)


def validate_comment_target(target_type, target_id):
    """校验评论对象是否合法，返回错误提示；合法返回空串"""
    if target_type not in COMMENT_TARGET_TYPES:
        return '评论对象类型不正确'
    if target_type == 'article':
        if not target_id or not is_valid_uuid(target_id):
            return '缺少文章 id'
        if not Article.objects.filter(id=target_id).exists():
            return '文章不存在'
    return ''


@require_POST
def get_client_comment_list(request):
    """
    评论列表：顶层评论分页（最新在前），每条内嵌其下全部回复（最早在前）。

    固定查询次数：顶层分页 + 回复 + 用户 + 回复数统计，不逐条查库。
    """
    params = post_handle(request)
    target_type = params.get('targetType')
    target_id = params.get('targetId') or None
    msg = validate_comment_target(target_type, target_id)
    if msg:
        return res_handle(501, msg, None)

    user_id = get_user_id(request)
    # 内容作者只查一次，用于逐条判定 canDelete
    target_author_id = get_target_author_id(target_type, target_id)
    target_sql = filter_target_comments(get_visible_comments(), target_type, target_id)

    root_sql = target_sql.filter(rootId__isnull=True).order_by('-createTime')
    root_total = root_sql.count()
    page_data = limit_queryset(params, root_sql)
    root_list = list(page_data['result'])
    root_ids = [root.id for root in root_list]

    reply_list = list(
        target_sql.filter(rootId__in=root_ids).order_by('createTime')) if root_ids else []
    reply_map = {}
    for reply in reply_list:
        reply_map.setdefault(str(reply.rootId), []).append(reply)

    user_ids = set()
    for comment in root_list + reply_list:
        user_ids.add(comment.user)
        if comment.replyUser:
            user_ids.add(comment.replyUser)
    user_map = build_user_map(user_ids)

    result = []
    for root in root_list:
        replies = [
            format_flat_comment(reply, user_map, can_delete_comment(user_id, reply.user, target_author_id))
            for reply in reply_map.get(str(root.id), [])
        ]
        result.append(format_root_comment(
            root, replies, user_map, can_delete_comment(user_id, root.user, target_author_id)))

    total_replies = target_sql.filter(rootId__isnull=False).count()
    return res_search({
        'total': root_total,
        'totalCount': root_total + total_replies,
        'result': result,
    })


@require_POST
def add_client_comment(request):
    """发表评论；带 rootId 时为回复该顶层评论下的某个人"""
    params = post_handle(request)
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录后再评论', None)

    target_type = params.get('targetType')
    target_id = params.get('targetId') or None
    msg = validate_comment_target(target_type, target_id)
    if msg:
        return res_handle(501, msg, None)

    msg = validate_add_comment_params(params)
    if msg:
        return res_handle(501, msg, None)

    root_id = params.get('rootId') or None
    reply_user = params.get('replyUser') or None
    if root_id:
        if not is_valid_uuid(root_id):
            return res_handle(501, '要回复的评论不存在', None)
        root = filter_target_comments(get_visible_comments(), target_type, target_id).filter(
            id=root_id, rootId__isnull=True).first()
        if not root:
            return res_handle(501, '要回复的评论不存在', None)
        if not reply_user or not is_valid_uuid(reply_user):
            return res_handle(501, '被回复人不存在', None)
        # 拦的是「回复自己」，不是「在别人回复了自己的楼层里继续回复」——
        # 后者 replyUser 是别人，必须放行，否则自己的评论一旦被回复就锁死了
        if str(reply_user) == str(user_id):
            return res_handle(501, '不能回复自己的评论', None)

    comment = Comment.objects.create(
        targetType=target_type,
        targetId=target_id,
        rootId=root_id,
        content=params.get('content').strip(),
        user=user_id,
        replyUser=reply_user,
        ip=request.META.get('REMOTE_ADDR'),
    )

    target_author_id = get_target_author_id(target_type, target_id)
    user_map = build_user_map({comment.user, comment.replyUser})
    return res_handle(0, '评论成功', format_flat_comment(
        comment, user_map, can_delete_comment(user_id, comment.user, target_author_id)))


@require_POST
def delete_client_comment(request):
    """删除评论：评论作者本人，或评论对象所属内容的作者（博主）"""
    params = post_handle(request)
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录', None)

    comment_id = params.get('id')
    if not comment_id or not is_valid_uuid(comment_id):
        return res_handle(501, '评论不存在', None)

    comment = get_visible_comments().filter(id=comment_id).first()
    if not comment:
        return res_handle(404, '评论不存在', None)

    target_author_id = get_target_author_id(comment.targetType, comment.targetId)
    if not can_delete_comment(user_id, comment.user, target_author_id):
        return res_handle(403, '您没有权限删除该评论', None)

    comment.isDelete = True
    comment.save()
    # 顶层评论删除时，其下回复一并软删
    if not comment.rootId:
        get_visible_comments().filter(rootId=comment.id).update(isDelete=True)
    return res_handle(0, '删除成功', True)
