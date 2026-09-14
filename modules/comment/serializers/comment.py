from modules.user.models import Users


def build_user_map(user_ids):
    """批量取评论涉及的用户，避免逐条查用户表（评论列表靠它规避 N+1）"""
    ids = [uid for uid in user_ids if uid]
    if not ids:
        return {}
    users = Users.objects.filter(id__in=ids).values('id', 'nickName', 'avatar')
    return {str(user['id']): user for user in users}


def format_user(user_map, user_id):
    """用户展示信息；用户已注销时降级为占位昵称，避免前端取空崩溃"""
    if not user_id:
        return None
    user = user_map.get(str(user_id))
    if not user:
        return {'id': str(user_id), 'nickName': '已注销用户', 'avatar': None}
    return {
        'id': str(user['id']),
        'nickName': user['nickName'] or '匿名用户',
        'avatar': user['avatar'],
    }


def format_flat_comment(comment, user_map, can_delete):
    """
    扁平结构：用于新增接口的返回，以及顶层评论下的回复项。

    rootId 为空表示这是一条顶层评论（前端据此判断插入位置）。
    """
    return {
        'id': str(comment.id),
        'content': comment.content,
        'createTime': comment.createTime,
        'canDelete': can_delete,
        'rootId': str(comment.rootId) if comment.rootId else None,
        'user': format_user(user_map, comment.user),
        'replyUser': format_user(user_map, comment.replyUser),
    }


def format_root_comment(comment, replies, user_map, can_delete):
    """顶层评论：内嵌其下全部回复"""
    return {
        'id': str(comment.id),
        'content': comment.content,
        'createTime': comment.createTime,
        'canDelete': can_delete,
        'user': format_user(user_map, comment.user),
        'replies': replies,
    }
