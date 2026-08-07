from datetime import datetime

from django.views.decorators.http import require_POST

from modules.system.models import Dictionary
from modules.system.service.dictionary import validate_add_dict_params
from utils.response import res_handle, res_search
from utils.tools import post_handle


@require_POST
def add_dictionary(request):
    params = post_handle(request)
    msg = validate_add_dict_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Dictionary.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_dictionary(request):
    params = post_handle(request)
    msg = validate_add_dict_params(params, params['id'])
    params['updateTime'] = datetime.now()
    if msg:
        return res_handle(501, msg, False)
    Dictionary.objects.filter(id=params['id']).update(**params)

    return res_handle(0, '修改成功', True)


@require_POST
def delete_dictionary(request):
    params = post_handle(request)
    sql = Dictionary.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def change_dictionary_status(request):
    params = post_handle(request)
    sql = Dictionary.objects.filter(id=params['id']).first()
    sql.status = params['status']
    sql.save()
    return res_handle(0, '修改成功', True)


@require_POST
def get_dictionary_list(request):
    params = post_handle(request)
    sql = Dictionary.objects.filter(code=params['code']).values(
        *['id', 'key', 'value', 'code', 'sort', 'desc', 'status', 'createTime', 'updateTime'])
    return res_search(list(sql))


@require_POST
def get_available_dictionary_list(request):
    params = post_handle(request)
    sql = Dictionary.objects.filter(code=params['code'], status=True).values(
        *['id', 'key', 'value'])
    return res_search(list(sql))
