from modules.notice.models import Notice

# 通知类型；新增点赞 / 收藏等类型时在这里扩展
NOTICE_TYPES = ('article_comment', 'comment_reply')


def build_comment_notices(comment, target_author_id):
    """
    按一条新评论推导出「要发给谁、发什么类型」，返回 [(recipient, type)]。

    规则（顺序即优先级，同一接收人只保留先命中的一条）：
    1. 回复了某人的评论 → 该类型最具体，优先通知被回复者
    2. 评论出现在文章 / 留言板下 → 通知内容作者

    去重与排除：被回复者恰是内容作者时只发一条 comment_reply；
    自己评论自己的内容、自己回复自己（前台已拦）都不产生通知。
    """
    candidates = []
    if comment.replyUser:
        candidates.append((str(comment.replyUser), 'comment_reply'))
    if target_author_id:
        candidates.append((str(target_author_id), 'article_comment'))

    sender = str(comment.user)
    recipients = []
    seen = set()
    for recipient, notice_type in candidates:
        if recipient == sender or recipient in seen:
            continue
        seen.add(recipient)
        recipients.append((recipient, notice_type))
    return recipients


def create_comment_notices(comment, target_author_id):
    """
    评论落库后写入通知。

    通知属于附带产物：写失败不应连带评论接口报错，异常由调用方兜底。
    """
    recipients = build_comment_notices(comment, target_author_id)
    if not recipients:
        return
    Notice.objects.bulk_create([
        Notice(
            recipient=recipient,
            sender=comment.user,
            type=notice_type,
            sourceId=comment.id,
            targetType=comment.targetType,
            targetId=comment.targetId,
            rootId=comment.rootId,
        )
        for recipient, notice_type in recipients
    ])


def get_unread_count(user_id):
    """当前用户未读消息数，供顶部角标使用"""
    if not user_id:
        return 0
    return Notice.objects.filter(recipient=user_id, isRead=False).count()
