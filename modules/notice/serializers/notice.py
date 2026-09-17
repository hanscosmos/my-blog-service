from modules.article.models import Article
from modules.comment.models import Comment
from modules.comment.serializers.comment import format_user

# 消息里只展示摘要，长 markdown 正文会把列表撑爆
MAX_EXCERPT_LENGTH = 120

# 非文章类评论对象的展示名（文章展示标题，见 format_target_name）
TARGET_TYPE_NAMES = {'message': '留言板'}


def excerpt(content):
    """评论摘要：压平换行并截断"""
    text = ' '.join((content or '').split())
    if len(text) <= MAX_EXCERPT_LENGTH:
        return text
    return text[:MAX_EXCERPT_LENGTH] + '...'


def build_article_title_map(target_ids):
    """批量取评论对象为文章的标题，避免逐条查文章表"""
    ids = [item for item in target_ids if item]
    if not ids:
        return {}
    article_list = Article.objects.filter(id__in=ids).values('id', 'title')
    return {str(item['id']): item['title'] for item in article_list}


def build_comment_map(notices):
    """
    批量取通知涉及的评论：触发评论 + 被回复的顶层评论。

    合并成一张以评论 id 为键的 map，格式化时按需取用，全程只有两次查询。
    """
    source_ids = {notice.sourceId for notice in notices}
    comment_list = list(Comment.objects.filter(id__in=source_ids).values(
        'id', 'content', 'status', 'isDelete', 'rootId'))
    root_ids = {item['rootId'] for item in comment_list if item['rootId']}
    if root_ids:
        comment_list += list(Comment.objects.filter(id__in=root_ids).values(
            'id', 'content', 'status', 'isDelete', 'rootId'))
    return {str(item['id']): item for item in comment_list}


def pick_comment(comment_map, comment_id):
    """取可见评论；已删除或被隐藏的返回 None，由格式化降级为占位文案"""
    if not comment_id:
        return None
    comment = comment_map.get(str(comment_id))
    if not comment or comment['isDelete'] or comment['status'] != 'visible':
        return None
    return comment


def format_target_name(notice, title_map):
    """评论对象展示名：文章标题 / 留言板；文章已删除时给占位文案"""
    if notice.targetType == 'article':
        return title_map.get(str(notice.targetId)) or '文章已删除'
    return TARGET_TYPE_NAMES.get(notice.targetType, notice.targetType)


def format_notice(notice, user_map, comment_map, title_map):
    """
    单条消息：只给事实字段，文案由前端按 type 拼接。

    isDeleted 表示触发的评论已不可见（删除 / 隐藏 / 数据缺失），
    此时 content 为空，前端不提供跳转。
    """
    comment = pick_comment(comment_map, notice.sourceId)
    root_comment = pick_comment(comment_map, notice.rootId)
    return {
        'id': str(notice.id),
        'type': notice.type,
        'isRead': notice.isRead,
        'createTime': notice.createTime,
        'sender': format_user(user_map, notice.sender),
        'content': excerpt(comment['content']) if comment else '',
        'isDeleted': comment is None,
        'rootContent': excerpt(root_comment['content']) if root_comment else '',
        'targetType': notice.targetType,
        'targetId': str(notice.targetId) if notice.targetId else None,
        'targetName': format_target_name(notice, title_map),
        'sourceId': str(notice.sourceId),
    }
