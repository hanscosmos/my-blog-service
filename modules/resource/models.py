import uuid
from django.db import models


class Icon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='icon_id')
    name = models.CharField(max_length=64)
    url = models.URLField()
    source = models.CharField(max_length=32)
    category = models.UUIDField(db_column='category_id')
    desc = models.CharField(max_length=64, db_column='description', null=True, blank=True)
    sort = models.IntegerField(default=0)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'sys_icon'
        ordering = ['sort']


class IconCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='category_id')
    name = models.CharField(max_length=64)
    value = models.CharField(max_length=64)
    sort = models.IntegerField(default=0)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'sys_icon_category'
        ordering = ['sort']


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='image_id')
    name = models.CharField(max_length=64)
    url = models.URLField()
    category = models.UUIDField(db_column='category_id')
    desc = models.CharField(max_length=64, db_column='description', null=True, blank=True)
    sort = models.IntegerField(default=0)
    isVisible = models.BooleanField(default=False, db_column='is_visible')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'sys_image'
        ordering = ['sort']


class ImageCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='category_id')
    name = models.CharField(max_length=64)
    value = models.CharField(max_length=64)
    sort = models.IntegerField(default=0)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'sys_image_category'
        ordering = ['sort']
