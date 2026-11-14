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


class FundHolding(models.Model):
    """用户基金持仓；category 表示资产类别，style 表示主动/被动管理方式"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='holding_id')
    user = models.UUIDField(db_column='user_id')
    fundCode = models.CharField(max_length=10, db_column='fund_code')
    fundName = models.CharField(max_length=128, db_column='fund_name')
    fundType = models.CharField(max_length=64, null=True, blank=True, db_column='fund_type')
    category = models.CharField(max_length=16, db_column='category')
    style = models.CharField(max_length=16, default='unknown', db_column='style')
    shares = models.DecimalField(max_digits=18, decimal_places=4, db_column='shares')
    costNav = models.DecimalField(max_digits=10, decimal_places=4, db_column='cost_nav')
    realizedPnl = models.DecimalField(max_digits=18, decimal_places=2, default=0, db_column='realized_pnl')
    remark = models.CharField(max_length=255, null=True, blank=True)
    sort = models.IntegerField(default=0)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')

    class Meta:
        db_table = 'sys_fund_holding'
        db_table_comment = '用户基金持仓'
        unique_together = ('user', 'fundCode')
        indexes = [
            models.Index(fields=['user'], name='idx_fund_holding_user'),
        ]
        ordering = ['sort', 'createTime']


class CashHolding(models.Model):
    """用户现金/存款资产；kind=money_fund 表示余额宝等货币基金，deposit 表示银行存款"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='holding_id')
    user = models.UUIDField(db_column='user_id')
    kind = models.CharField(max_length=16, db_column='kind')
    name = models.CharField(max_length=128, db_column='name')
    fundCode = models.CharField(max_length=10, null=True, blank=True, db_column='fund_code')
    balance = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column='balance')
    principal = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column='principal')
    annualRate = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, db_column='annual_rate')
    yesterdayPnl = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, db_column='yesterday_pnl')
    startDate = models.DateField(null=True, blank=True, db_column='start_date')
    endDate = models.DateField(null=True, blank=True, db_column='end_date')
    interestType = models.CharField(max_length=16, null=True, blank=True, db_column='interest_type')
    remark = models.CharField(max_length=255, null=True, blank=True)
    sort = models.IntegerField(default=0)
    createTime = models.DateTimeField(auto_now_add=True, db_column='create_time')
    updateTime = models.DateTimeField(auto_now=True, db_column='update_time')

    class Meta:
        db_table = 'sys_cash_holding'
        db_table_comment = '用户现金存款资产'
        indexes = [
            models.Index(fields=['user'], name='idx_cash_holding_user'),
        ]
        ordering = ['sort', 'createTime']
