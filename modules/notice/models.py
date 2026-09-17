import uuid

from django.db import models


class Notice(models.Model):
    """
    站内消息提醒：一条评论可能给多个人产生通知，按 recipient 拆成多行。

    - 只存 id 与关系，不存评论内容快照；列表接口批量回查评论表，
      评论被删/被隐藏时自然降级为「该评论已删除」，不会留下过期文案
    - 关联一律用裸 UUID，与项目其它模型一致
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='notice_id')
    # 接收人：内容作者（文章作者 / 博主），或评论被回复的人
    recipient = models.UUIDField(db_column='recipient_id')
    # 触发人：发表评论的人
    sender = models.UUIDField(db_column='sender_id')
    # 类型：article_comment 内容被评论 / comment_reply 评论被回复
    # 预留 article_like / comment_like / system
    type = models.CharField(max_length=32, db_column='notice_type')
    # 触发源类型：comment（预留 article / user）
    sourceType = models.CharField(max_length=32, default='comment', db_column='source_type')
    # 触发源 id：评论 id。点击消息时据此定位，也是回查内容摘要的依据
    sourceId = models.UUIDField(db_column='source_id')
    # 评论对象，与 blog_comment 同口径：article 文章 / message 留言板
    targetType = models.CharField(max_length=32, db_column='target_type')
    targetId = models.UUIDField(null=True, blank=True, db_column='target_id')
    # 仅 comment_reply 有值：被回复的顶层评论，用于展示「回复了你的评论」
    rootId = models.UUIDField(null=True, blank=True, db_column='root_id')
    isRead = models.BooleanField(default=False, db_column='is_read')
    readTime = models.DateTimeField(null=True, blank=True, db_column='read_time')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'blog_notice'
        # 消息列表最新在前；角标未读数与列表筛选都走 recipient + isRead 联合索引
        ordering = ['-createTime']
        indexes = [
            models.Index(fields=['recipient', 'isRead', 'createTime']),
        ]
