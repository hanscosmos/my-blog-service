# Create your models here.
import uuid
from django.db import models
from config.choices import COLOR_CHOICES, MODULE_CHOICES


class Menu(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='menu_id')
    name = models.CharField(max_length=64, db_column='menu_name')
    code = models.CharField(max_length=64, db_column='menu_code')
    route = models.CharField(max_length=64, db_column='menu_route')
    icon = models.URLField(blank=True, null=True)
    father = models.UUIDField(null=True, blank=True, db_column='parent_id')
    sort = models.IntegerField(default=0)
    color = models.CharField(max_length=32, choices=COLOR_CHOICES, null=True, blank=True)
    type = models.CharField(max_length=32, db_column='menu_type')

    class Meta:
        db_table = 'sys_menu'
        ordering = ['sort']


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='role_id')
    name = models.CharField(max_length=32, db_column='role_name')
    code = models.CharField(max_length=32, db_column='role_code')
    sort = models.IntegerField(default=0)
    limit = models.IntegerField(blank=True, null=True, db_column='limit')

    class Meta:
        db_table = 'sys_role'
        ordering = ['sort']


class Api(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='api_id')
    name = models.CharField(max_length=64, db_column='api_name')
    path = models.CharField(max_length=64, db_column='api_path')
    code = models.CharField(max_length=64, db_column='api_code')
    sort = models.IntegerField(default=0)
    module = models.CharField(max_length=32, choices=MODULE_CHOICES)

    class Meta:
        db_table = 'sys_api'


class MenuAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    menu = models.UUIDField(Menu, db_column='menu_id')
    role = models.UUIDField(Role, db_column='role_id')
    isForbidden = models.BooleanField(default=False, db_column='is_forbidden')

    class Meta:
        db_table = 'sys_authority_menu'


class ApiAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    api = models.UUIDField(Api, db_column='api_id')
    role = models.UUIDField(Role, db_column='role_id')
    isForbidden = models.BooleanField(default=False, db_column='is_forbidden')

    class Meta:
        db_table = 'sys_authority_api'

