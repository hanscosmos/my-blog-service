import uuid

from django.db import models


class Comment(models.Model):
    """
    博客评论：一张表承载所有评论类型。

    - 靠 targetType + targetId 区分评论对象（文章评论 / 留言板 / 未来的随笔等）
    - 靠 rootId 表达两级结构：顶层评论 rootId 为空，回复统一挂在所属顶层评论下（扁平）
    - 被回复者记在 replyUser 上，渲染为「A 回复 B」
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='comment_id')
    # 评论对象类型：article 文章评论 / message 留言板
    targetType = models.CharField(max_length=32, db_column='target_type')
    # 评论对象 id；留言板没有具体对象，为空
    targetId = models.UUIDField(null=True, blank=True, db_column='target_id')
    # 顶层评论为空；回复时指向所属顶层评论
    rootId = models.UUIDField(null=True, blank=True, db_column='root_id')
    # 评论正文，存 markdown 源码（含图片链接），长度上限见 service/comment.py 的 MAX_CONTENT_LENGTH
    content = models.TextField(db_column='comment_content')
    # 评论人；关联用户用裸 UUID，与项目其它模型一致
    user = models.UUIDField(db_column='user_id')
    # 被回复者，用于展示「A 回复 B」
    replyUser = models.UUIDField(null=True, blank=True, db_column='reply_user_id')
    # 先发后审：默认可见，后续后台可置为 hidden
    status = models.CharField(max_length=32, default='visible', db_column='status')
    ip = models.GenericIPAddressField(null=True, blank=True)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    isDelete = models.BooleanField(default=False, db_column='is_delete')

    class Meta:
        db_table = 'blog_comment'
        ordering = ['createTime']
        indexes = [
            models.Index(fields=['targetType', 'targetId', 'rootId']),
        ]
