from django.views.decorators.http import require_POST

from modules.resource.models import Icon, IconCategory
from modules.resource.service.common import validate_add_category_params
from modules.resource.service.icon import validate_add_icon_params
from utils.response import res_handle, res_limit
from utils.tools import post_handle


@require_POST
def add_icon(request):
    params = post_handle(request)
    msg = validate_add_icon_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Icon.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_icon(request):
    params = post_handle(request)
    msg = validate_add_icon_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Icon.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_icon(request):
    params = post_handle(request)
    sql = Icon.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_icon_list(request):
    params = post_handle(request)
    sql = Icon.objects.filter(name__contains=params['name']).values(
        *['id', 'name', 'url', 'source', 'sort', 'category', 'createTime'])
    if params['category']:
        sql = sql.filter(category=params['category'])
    return res_limit(params, sql)


@require_POST
def add_icon_category(request):
    params = post_handle(request)
    sql = IconCategory.objects.filter(name=params['name'])
    msg = validate_add_category_params(params, None, sql)
    if msg:
        return res_handle(501, False, msg)
    IconCategory.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_icon_category(request):
    params = post_handle(request)
    sql = IconCategory.objects.filter(name=params['name'])
    msg = validate_add_category_params(params, params['id'], sql)
    if msg:
        return res_handle(501, False, msg)
    IconCategory.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_icon_category(request):
    params = post_handle(request)
    sql = IconCategory.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


def get_icon_category_list(request):
    role_list = IconCategory.objects.all().values(*['id', 'name', 'value', 'sort', 'createTime'])
    return res_handle(0, '查询成功', list(role_list))
