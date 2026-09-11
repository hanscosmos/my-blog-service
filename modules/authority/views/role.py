from django.db import transaction
from django.views.decorators.http import require_POST

from modules.authority.models import MenuAuthority, Role
from modules.authority.service.role import (
    validate_add_role_params,
    validate_delete_role_params,
    validate_edit_role_params,
    validate_set_role_menu_params,
)
from utils.response import res_handle
from utils.tools import post_handle

ROLE_FORM_KEYS = ('name', 'code', 'sort', 'limit')


def _pick_role_form(params):
    return {key: params[key] for key in ROLE_FORM_KEYS if key in params}


@require_POST
def add_role(request):
    params = post_handle(request)
    msg = validate_add_role_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Role.objects.create(**_pick_role_form(params))
    return res_handle(0, '添加成功', True)


@require_POST
def edit_role(request):
    params = post_handle(request)
    msg = validate_edit_role_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Role.objects.filter(id=params['id']).update(**_pick_role_form(params))
    return res_handle(0, '修改成功', True)


@require_POST
def delete_role(request):
    params = post_handle(request)
    ids = params.get('ids') or []
    msg = validate_delete_role_params(ids)
    if msg:
        return res_handle(501, msg, False)
    with transaction.atomic():
        MenuAuthority.objects.filter(role__in=ids).delete()
        Role.objects.filter(id__in=ids).delete()
    return res_handle(0, '删除成功', True)


def get_role_list(request):
    role_list = Role.objects.all()
    return res_handle(0, '查询成功', list(role_list))


@require_POST
def set_role_menu(request):
    """给角色分配菜单 / 操作权限（覆盖式全量设置）"""
    params = post_handle(request)
    role_id, menu_ids = params.get('roleId'), params.get('menuIds') or []
    msg = validate_set_role_menu_params(role_id, menu_ids)
    if msg:
        return res_handle(501, msg, False)
    with transaction.atomic():
        MenuAuthority.objects.filter(role=role_id).delete()
        MenuAuthority.objects.bulk_create(
            [MenuAuthority(menu=menu_id, role=role_id) for menu_id in menu_ids]
        )
    return res_handle(0, '权限分配成功', True)


def get_menu_list_by_role(request):
    """查询角色已分配的菜单 id 列表"""
    role_id = request.GET.get('id')
    if not role_id:
        return res_handle(501, '请选择要查询的角色', {'menuIds': []})
    menu_ids = list(
        MenuAuthority.objects.filter(role=role_id).values_list('menu', flat=True)
    )
    return res_handle(0, '查询成功', {'menuIds': menu_ids})
