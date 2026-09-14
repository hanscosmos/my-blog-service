from uuid import UUID

from modules.article.models import Article
from modules.blogger.models import BloggerProfile

# 允许的评论对象类型，新增评论类型（如随笔）时在这里扩展
COMMENT_TARGET_TYPES = ('article', 'message')

MAX_CONTENT_LENGTH = 500


def is_valid_uuid(value):
    """校验是否为合法 UUID，避免非法 id 直接进 ORM 查询抛 500"""
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def validate_add_comment_params(params):
    """校验新增评论的入参，返回错误提示；无错误返回空串"""
    msg = ''
    content = (params.get('content') or '').strip()
    if not content:
        msg = '评论内容不能为空'
    elif len(content) > MAX_CONTENT_LENGTH:
        msg = '评论内容不能超过%d个字' % MAX_CONTENT_LENGTH
    return msg


def get_target_author_id(target_type, target_id):
    """
    取评论对象所属内容的作者（博主）user id，用于判定删除权限。

    - article：文章作者
    - message：博主本人（沿用前台关于页取博主的写法）
    """
    if target_type == 'article':
        if not target_id or not is_valid_uuid(target_id):
            return None
        article = Article.objects.filter(id=target_id).first()
        return article.author if article else None
    if target_type == 'message':
        profile = BloggerProfile.objects.order_by('createdAt').first()
        return profile.userId if profile else None
    return None


def can_delete_comment(user_id, comment_user_id, target_author_id):
    """
    删除权限判定：评论作者本人，或评论对象所属内容的作者（博主）。

    评论列表（算 canDelete）与删除接口共用此函数，避免两处规则漂移。
    """
    if not user_id:
        return False
    if str(comment_user_id) == str(user_id):
        return True
    if not target_author_id:
        return False
    return str(target_author_id) == str(user_id)
