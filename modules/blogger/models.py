import uuid

from django.db import models


class BloggerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='profile_id')
    userId = models.UUIDField(db_column='user_id')
    introduction = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    wechat = models.CharField(max_length=64, null=True, blank=True)
    qq = models.CharField(max_length=32, null=True, blank=True)
    github = models.URLField(max_length=255, null=True, blank=True)
    weibo = models.URLField(max_length=255, null=True, blank=True)
    site = models.URLField(max_length=255, null=True, blank=True)
    resumeFileUrl = models.URLField(max_length=500, null=True, blank=True, db_column='resume_file_url')
    resumeFileName = models.CharField(max_length=255, null=True, blank=True, db_column='resume_file_name')
    assets = models.JSONField(default=dict, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'blogger_profile'
