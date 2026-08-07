import uuid
from django.db import models


class ArticleCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='category_id')
    name = models.CharField(max_length=32)
    alias = models.CharField(max_length=64)
    father = models.UUIDField(null=True, blank=True)
    sort = models.SmallIntegerField(null=True, blank=True, default=0)
    description = models.CharField(max_length=64, null=True, blank=True)
    createTime = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blog_article_category'
        ordering = ['sort']


class ArticleTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='tag_id')
    name = models.CharField(max_length=32, db_column='name')
    alias = models.CharField(max_length=32, db_column='alias')
    sort = models.SmallIntegerField(null=True, blank=True, default=0)
    color = models.CharField(max_length=32, db_column='color', default='blue')
    description = models.CharField(max_length=64, db_column='description', null=True, blank=True)
    createTime = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blog_article_tag'
        ordering = ['sort']


class ArticleColumn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='column_id')
    name = models.CharField(max_length=32, db_column='name')
    sort = models.SmallIntegerField(null=True, blank=True, default=0)
    user = models.UUIDField(db_column='user_id')
    cover = models.URLField(max_length=200, null=True, blank=True, default=None)
    description = models.CharField(max_length=200, db_column='description', null=True, blank=True)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')

    class Meta:
        db_table = 'blog_article_column'
        ordering = ['sort']


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='article_id')
    title = models.CharField(max_length=32, db_column='article_title')
    pinyin = models.CharField(max_length=128, db_column='pinyin_title')
    category = models.UUIDField(db_column='category_id', null=True, blank=True)
    author = models.UUIDField(db_column='author_id')
    status = models.CharField(max_length=32, db_column='status', default='publish')
    properties = models.CharField(max_length=32, db_column='properties')
    visible = models.CharField(max_length=32, db_column='visible')
    column = models.UUIDField(null=True, blank=True, default=None, db_column='column_id')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    updateTime = models.DateTimeField(db_column='update_time')
    readCount = models.IntegerField(default=0, db_column='read_count')
    cover = models.URLField(max_length=200, null=True, blank=True)
    isTop = models.BooleanField(default=False, db_column='is_top')
    abstract = models.CharField(max_length=100, db_column='article_abstract', null=True, blank=True)
    isDelete = models.BooleanField(default=False, db_column='is_delete')

    class Meta:
        db_table = 'blog_article'
        ordering = ['-isTop', '-createTime']


class ArticleReadLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='read_log_id')
    article = models.UUIDField(db_column='article_id')
    user = models.UUIDField(null=True, blank=True, db_column='user_id')
    ip = models.GenericIPAddressField(null=True, blank=True, db_column='ip')
    readTime = models.DateTimeField(auto_now_add=True, db_column='read_time')

    class Meta:
        db_table = 'blog_article_read_log'
        ordering = ['-readTime']


class ArticleDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='article_detail_id')
    article = models.UUIDField(db_column='article_id')
    content = models.TextField()

    class Meta:
        db_table = 'blog_article_detail'


class ArticleTagRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='article_tag_id')
    tag = models.UUIDField(db_column='tag_id')
    article = models.UUIDField(db_column='article_id')

    class Meta:
        db_table = 'blog_article_tag_relation'
