import uuid
from django.db import models
from django.utils import timezone


class Dictionary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='dict_id')
    code = models.CharField(max_length=64, db_column='dict_code')
    key = models.CharField(max_length=64, db_column='dict_key')
    value = models.CharField(max_length=64, db_column='dict_value')
    desc = models.CharField(max_length=64, db_column='description', null=True, blank=True)
    sort = models.IntegerField(default=0)
    status = models.BooleanField(default=True)
    createTime = models.DateTimeField(default=timezone.now, editable=False, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')

    class Meta:
        db_table = 'sys_dictionary'
        ordering = ['sort']


class UpdateLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='log_id')
    summary = models.CharField(max_length=64, db_column='summary')
    version = models.CharField(max_length=32, db_column='version')
    plannedReleaseDate = models.DateTimeField(db_column='planned_release_date')
    actualReleaseDate = models.DateTimeField(null=True, blank=True, default=None, db_column='actual_release_date')
    releasedBy = models.UUIDField(max_length=64, db_column='released_by')
    releasedType = models.CharField(max_length=32, db_column='released_type')
    status = models.CharField(max_length=64, db_column='status')
    details = models.TextField()
    isCurrentVersion = models.BooleanField(default=False)
    createTime = models.DateTimeField(default=timezone.now, editable=False, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')

    class Meta:
        db_table = 'sys_update_log'
        ordering = ['createTime']
