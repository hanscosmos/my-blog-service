import uuid
from django.db import models


class AiConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='conversation_id')
    user = models.UUIDField(db_column='user_id')
    title = models.CharField(max_length=64)
    model = models.CharField(max_length=32, default='deepseek-v4-pro')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')

    class Meta:
        db_table = 'blog_ai_conversation'
        ordering = ['-updateTime']


class AiMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='message_id')
    conversation = models.UUIDField(db_column='conversation_id')
    role = models.CharField(max_length=16)
    content = models.TextField()
    promptTokens = models.IntegerField(null=True, blank=True, db_column='prompt_tokens')
    completionTokens = models.IntegerField(null=True, blank=True, db_column='completion_tokens')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'blog_ai_message'
        ordering = ['createTime']
