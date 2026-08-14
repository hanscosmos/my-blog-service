import uuid

from django.db import models


class Users(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='user_id')
    nickName = models.CharField(max_length=32, null=True, blank=True, db_column='nick_name')
    username = models.CharField(max_length=32)
    password = models.CharField(max_length=128)
    avatar = models.URLField(max_length=255, null=True, blank=True)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    isForbidden = models.BooleanField(default=False, db_column='is_forbidden')

    class Meta:
        db_table = 'sys_user'
        ordering = ['createTime']


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, db_column='user_id')
    sex = models.CharField(max_length=16, default='2', null=True, blank=True)
    email = models.CharField(max_length=64, null=True, blank=True)
    bgCover = models.URLField(max_length=800, null=True, blank=True, db_column='bg_cover')
    talks = models.CharField(max_length=255, null=True, blank=True)
    wechat = models.CharField(max_length=255, null=True, blank=True)
    levelScore = models.IntegerField(default=0)

    loginTime = models.DateTimeField(db_column='last_login_time', null=True, blank=True)

    class Meta:
        db_table = 'sys_user_profile'


class UserAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.UUIDField(db_column='user_id')
    role = models.UUIDField(db_column='role_id')
    isForbidden = models.BooleanField(default=False, db_column='is_forbidden')

    class Meta:
        db_table = 'sys_user_role'


class UserOtherApps(models.Model):
    user = models.UUIDField(primary_key=True, db_column='user_id')
    type = models.CharField(max_length=32, null=True, blank=True)
    appId = models.CharField(max_length=255, null=True, blank=True)
    unionId = models.CharField(max_length=255)
    credential = models.CharField(max_length=255)

    class Meta:
        db_table = 'sys_user_other_apps'


class UserTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.UUIDField(db_column='user_id')
    title = models.CharField(max_length=64)
    tags = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    priority = models.CharField(max_length=32)
    status = models.CharField(max_length=32)
    deadline = models.DateTimeField(null=True, blank=True)
    startTime = models.DateTimeField(null=True, blank=True, db_column='start_time')
    endTime = models.DateTimeField(null=True, blank=True, db_column='end_time')
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')
    importance = models.IntegerField(default=3)      # 1-5
    urgency = models.IntegerField(default=3)         # 1-5
    growth = models.IntegerField(default=3)          # 1-5
    happiness = models.IntegerField(default=3)       # 1-5
    negative = models.IntegerField(default=0)        # 0 ~ -5
    remindBeforeMinutes = models.IntegerField(default=-1, db_column='remind_before_minutes')  # -1=不提醒，单位分钟

    @property
    def value_score(self):
        return (self.importance * 0.7 +
                self.urgency * 0.3) * ( self.growth * 0.7 +
                self.happiness * 0.3 - self.negative * 1.0)



    class Meta:
        db_table = 'sys_user_task'
        ordering = ['-deadline']


class UserActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.UUIDField(db_column='user_id')
    action = models.CharField(max_length=128)
    targetId = models.UUIDField(null=True, blank=True, db_column='target_id')   # 操作对象（如文章ID）
    targetType = models.CharField(max_length=50, blank=True, db_column='target_type')  # 操作对象类型（Post/Comment...）
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    extraData = models.JSONField(default=dict, blank=True, db_column='extra_data')

    class Meta:
        indexes = [
            models.Index(fields=["user", "targetType"]),
            models.Index(fields=["createTime"]),
        ]
        db_table = 'sys_user_activity_log'
        ordering = ["-createTime"]


class UserActivitySummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.UUIDField(db_column='user_id')
    date = models.DateField()
    posts = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    logins = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0)

    class Meta:
        unique_together = ("user", "date")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["score"]),
        ]
        db_table = 'sys_user_activity_summary'


