from django.db.models import Q
from django.views.decorators.http import require_POST
from modules.authority.models import Api
from utils.response import res_handle, res_valid, res_delete, res_limit
from utils.tools import post_handle


@require_POST
def add_api(request):
    params = post_handle(request)
    sql = Api.objects.filter(Q(name=params['name']) | Q(btnSign=params['btnSign']))
    api_form = ApiForm(data=params)
    return res_valid(api_form, sql)


@require_POST
def batch_add_api(request):
    params = post_handle(request)
    api_list = params['apis']
    api_lists = []
    for item in api_list:
        api_lists.append(Api(name=item['name'], path=item['path'], module=item['module'], btnSign=item['btnSign'],
                             isAuth=item['isAuth'], sort=item['sort']))
    Api.objects.bulk_create(api_lists)
    return res_handle(0, '操作成功')


@require_POST
def edit_api(request):
    params = post_handle(request)
    sql = Api.objects.filter(Q(name=params['name']) | Q(btnSign=params['btnSign'])).exclude(id=params['id'])
    api_obj = Api.objects.get(id=params['id'])
    api_form = ApiForm(data=params, instance=api_obj)
    return res_valid(api_form, sql)


def get_api_list(request):
    params = post_handle(request)
    param = params['param']
    sql = Api.objects.all().order_by('sort')
    if obj_has_attr(param, 'name'):
        sql = sql.filter(name__contains=param['name'])
    if obj_has_attr(param, 'module'):
        sql = sql.filter(module__exact=param['module'])
    return res_limit(params, sql)


@require_POST
def delete_api_by_id(request):
    params = post_handle(request)
    row = Api.objects.get(id=params['id'])
    row.delete()
    return res_handle(0, '删除成功')


@require_POST
def delete_api_by_ids(request):
    params = post_handle(request)
    sql = Api.objects.filter(id__in=params['ids'])
    return res_delete(sql)