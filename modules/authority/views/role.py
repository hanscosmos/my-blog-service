from django.views.decorators.http import require_POST
from modules.authority.models import Role
from modules.authority.service.role import validate_add_role_params
from utils.response import res_handle
from utils.tools import post_handle


@require_POST
def add_role(request):
    params = post_handle(request)
    msg = validate_add_role_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Role.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_role(request):
    params = post_handle(request)
    msg = validate_add_role_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Role.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_role(request):
    params = post_handle(request)
    sql = Role.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


def get_role_list(request):
    role_list = Role.objects.all()
    return res_handle(0, '查询成功', list(role_list))

