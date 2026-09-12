from django.db import transaction
from django.views.decorators.http import require_POST

from config.choices import MENU_TYPE_BUTTON
from modules.authority.models import Menu, MenuAuthority
from modules.authority.serializers.menu import MenuSerializers
from modules.authority.service.menu import (
    validate_add_menu_params,
    validate_delete_menu_params,
)
from modules.authority.service.permission import get_user_nav_menu_ids
from utils.auth import get_user_id
from utils.response import res_handle
from utils.tools import post_handle, list_to_tree


@require_POST
def add_menu(request):
    params = post_handle(request)
    msg = validate_add_menu_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Menu.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_menu(request):
    params = post_handle(request)
    msg = validate_add_menu_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Menu.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_menu(request):
    params = post_handle(request)
    ids = params.get('ids') or []
    msg = validate_delete_menu_params(ids)
    if msg:
        return res_handle(501, msg, False)
    with transaction.atomic():
        # 菜单删除后同步清理角色授权记录，避免残留脏数据
        MenuAuthority.objects.filter(menu__in=ids).delete()
        Menu.objects.filter(id__in=ids).delete()
    return res_handle(0, '删除成功', True)


def get_menu_list(request):
    menu_list = Menu.objects.all()
    return res_handle(0, '查询成功', list(menu_list))


def get_all_menu_tree(request):
    menu_list = Menu.objects.all()
    new_menu_list = MenuSerializers(instance=menu_list, many=True)
    menu_tree = list_to_tree(new_menu_list.data, 'father', 'id')
    return res_handle(0, '查询成功', menu_tree)


def get_nav_menu_tree(request):
    """按当前用户角色返回侧边栏菜单树

    按钮节点与 isNav=False 的节点都不参与侧边栏渲染 —— 后者包括顶部导航栏入口、
    系统设置、个人中心这些「全局」页面，它们参与授权但不上侧边栏。
    直接按 isNav 过滤而不是 exclude：get_user_nav_menu_ids 会为子节点补齐祖先，
    若只 exclude 会把「全局」这类隐藏目录的父链重新带回来，渲染出空目录。
    """
    menu_list = list(Menu.objects.filter(isNav=True).exclude(type=MENU_TYPE_BUTTON))
    user_id = get_user_id(request)
    if user_id:
        allowed_ids = get_user_nav_menu_ids(user_id)
        menu_list = [menu for menu in menu_list if menu.id in allowed_ids]
    menu_tree = list_to_tree(menu_list, 'father', 'id')
    return res_handle(0, '查询成功', menu_tree)
