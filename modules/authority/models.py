# Create your models here.
import uuid
from django.db import models
from config.choices import COLOR_CHOICES


class Menu(models.Model):
    """菜单表：同时承载三级权限节点

    type = '1' 目录      （侧边栏分组，route 为空）
    type = '2' 页面      （route 为前端路由 name，侧边栏叶子，代表该页面的「读权限」）
    type = '3' 按钮/操作 （route 为空，code 即权限码，用于前端按钮显隐与后端接口校验）

    isNav = False 表示「不上侧边栏」：适用于顶部导航栏入口、系统设置、个人中心
    这类不在左侧菜单里的页面。它们同样参与角色授权，只是不下发给侧边栏渲染。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='menu_id')
    name = models.CharField(max_length=64, db_column='menu_name')
    code = models.CharField(max_length=64, db_column='menu_code')
    route = models.CharField(max_length=64, blank=True, default='', db_column='menu_route')
    icon = models.URLField(blank=True, null=True)
    father = models.UUIDField(null=True, blank=True, db_column='parent_id')
    sort = models.IntegerField(default=0)
    color = models.CharField(max_length=32, choices=COLOR_CHOICES, null=True, blank=True)
    type = models.CharField(max_length=32, db_column='menu_type')
    isNav = models.BooleanField(default=True, db_column='is_nav')

    class Meta:
        db_table = 'sys_menu'
        ordering = ['sort']


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column='role_id')
    name = models.CharField(max_length=32, db_column='role_name')
    code = models.CharField(max_length=32, db_column='role_code')
    sort = models.IntegerField(default=0)
    limit = models.IntegerField(blank=True, null=True, db_column='limit')
    isSuper = models.BooleanField(default=False, db_column='is_super')

    class Meta:
        db_table = 'sys_role'
        ordering = ['sort']


class MenuAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    menu = models.UUIDField(db_column='menu_id')
    role = models.UUIDField(db_column='role_id')
    isForbidden = models.BooleanField(default=False, db_column='is_forbidden')

    class Meta:
        db_table = 'sys_authority_menu'

