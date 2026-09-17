"""后台评论管理视图：查询 + 删除 + 禁用评论人。

与前台视图（modules/client/comment_views.py）的区别：
- 前台按 targetType + targetId 限定某个评论对象的评论，删除权限是「评论作者本人或内容作者」
- 后台不做对象限定，删除权限完全交给菜单权限码（system:comment:delete）控制
"""

from django.db.models import Q
from django.views.decorators.http import require_POST

from modules.article.models import Article
from modules.authority.service.permission import is_super_user
from modules.comment.models import Comment
from modules.comment.serializers.comment import build_user_map, format_admin_comment_user
from modules.comment.service.comment import is_valid_uuid
from modules.user.models import Users
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import limit_queryset, obj_has_attr, post_handle

# 评论对象类型的中文名（文章会额外取标题，这里只是兜底）
TARGET_TYPE_NAMES = {'article': '文章', 'message': '留言板'}


def build_article_title_map(comments):
    """批量取评论对象为文章的标题，避免逐条评论查文章表"""
    article_ids = {comment.targetId for comment in comments
                   if comment.targetType == 'article' and comment.targetId}
    if not article_ids:
        return {}
    article_list = Article.objects.filter(id__in=article_ids).values('id', 'title')
    return {str(item['id']): item['title'] for item in article_list}


def get_target_name(comment, title_map):
    """评论对象的展示名：文章标题 / 留言板；文章已被删除时给占位文案"""
    if comment.targetType == 'article':
        return title_map.get(str(comment.targetId)) or '文章已删除'
    return TARGET_TYPE_NAMES.get(comment.targetType, comment.targetType)


def format_admin_comment(comment, user_map, title_map):
    """后台评论项：顶层与回复同构，前端用同一套类型渲染"""
    return {
        'id': str(comment.id),
        'content': comment.content,
        'targetType': comment.targetType,
        'targetId': str(comment.targetId) if comment.targetId else None,
        'targetName': get_target_name(comment, title_map),
        'rootId': str(comment.rootId) if comment.rootId else None,
        'user': format_admin_comment_user(user_map, comment.user),
        'replyUser': format_admin_comment_user(user_map, comment.replyUser),
        'ip': comment.ip,
        'status': comment.status,
        'createTime': comment.createTime,
    }


@require_POST
def get_admin_comment_list(request):
    """
    后台评论列表：顶层评论分页（最新在前），每条内嵌其下全部回复（最早在前）。

    固定查询次数：顶层分页 + 回复 + 用户 + 文章标题，不逐条查库。
    """
    params = post_handle(request)
    sql = Comment.objects.filter(isDelete=False)
    if obj_has_attr(params, 'keyword'):
        sql = sql.filter(content__contains=params['keyword'])
    if obj_has_attr(params, 'targetType'):
        sql = sql.filter(targetType=params['targetType'])
    if obj_has_attr(params, 'userId'):
        sql = sql.filter(user=params['userId'])
    if obj_has_attr(params, 'status'):
        sql = sql.filter(status=params['status'])
    if obj_has_attr(params, 'startTime') and obj_has_attr(params, 'endTime'):
        sql = sql.filter(createTime__range=(params['startTime'], params['endTime']))

    # 从消息提醒跳转过来时按评论 id 定位：目标若是回复，改为取它所属的顶层评论，
    # 这样前端渲染时能连回复一起看到；定位是精确查询，覆盖其它筛选项
    focus_id = params.get('focusId')
    if focus_id and is_valid_uuid(focus_id):
        focus = Comment.objects.filter(id=focus_id, isDelete=False).first()
        sql = Comment.objects.filter(
            isDelete=False, id=focus.rootId if focus and focus.rootId else focus_id)

    root_sql = sql.filter(rootId__isnull=True).order_by('-createTime')
    queryset_data = limit_queryset(params, root_sql)
    root_list = list(queryset_data['result'])
    root_ids = [root.id for root in root_list]

    reply_list = list(sql.filter(rootId__in=root_ids).order_by('createTime')) if root_ids else []
    reply_map = {}
    for reply in reply_list:
        reply_map.setdefault(str(reply.rootId), []).append(reply)

    user_ids = set()
    for comment in root_list + reply_list:
        user_ids.add(comment.user)
        user_ids.add(comment.replyUser)
    user_map = build_user_map(user_ids)
    title_map = build_article_title_map(root_list + reply_list)

    result = []
    for root in root_list:
        root_data = format_admin_comment(root, user_map, title_map)
        root_data['replies'] = [
            format_admin_comment(reply, user_map, title_map)
            for reply in reply_map.get(str(root.id), [])
        ]
        result.append(root_data)

    return res_search({'total': queryset_data['total'], 'result': result})


@require_POST
def delete_admin_comment(request):
    """删除评论：软删（与前台一致），删除顶层评论时其下回复一并软删"""
    params = post_handle(request)
    ids = params.get('ids') or []
    if not ids:
        return res_handle(501, '请选择要删除的评论', None)
    if not all(is_valid_uuid(item) for item in ids):
        return res_handle(501, '评论不存在', None)

    delete_count = Comment.objects.filter(
        isDelete=False
    ).filter(Q(id__in=ids) | Q(rootId__in=ids)).update(isDelete=True)
    return res_handle(0, '删除成功', delete_count)


@require_POST
def forbid_comment_user(request):
    """禁用 / 解禁评论人：写 Users.isForbidden，被禁用的用户无法登录、写接口被中间件拦截"""
    params = post_handle(request)
    user_id = params.get('userId')
    is_forbidden = bool(params.get('isForbidden'))
    if not is_valid_uuid(user_id) or not Users.objects.filter(id=user_id).exists():
        return res_handle(501, '用户不存在', None)

    if is_forbidden:
        if str(user_id) == str(get_user_id(request)):
            return res_handle(501, '不能禁用自己', None)
        if is_super_user(user_id):
            return res_handle(501, '不能禁用超级管理员', None)

    Users.objects.filter(id=user_id).update(isForbidden=is_forbidden)
    return res_handle(0, '已禁用该用户' if is_forbidden else '已解除禁用', True)
