from django.views.decorators.http import require_POST

from modules.resource.models import Image, ImageCategory
from modules.resource.service.common import validate_add_category_params
from modules.resource.service.image import validate_add_image_params
from utils.response import res_handle, res_limit
from utils.tools import post_handle


@require_POST
def add_image(request):
    params = post_handle(request)
    msg = validate_add_image_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Image.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_image(request):
    params = post_handle(request)
    msg = validate_add_image_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Image.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_image(request):
    params = post_handle(request)
    sql = Image.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_image_list(request):
    params = post_handle(request)
    sql = Image.objects.filter(name__contains=params['name']).values(
        *['id', 'name', 'url', 'isVisible', 'sort', 'category', 'createTime'])
    if params['category']:
        sql = sql.filter(category=params['category'])
    return res_limit(params, sql)


@require_POST
def add_image_category(request):
    params = post_handle(request)
    sql = ImageCategory.objects.filter(name=params['name'])
    msg = validate_add_category_params(params, None, sql)
    if msg:
        return res_handle(501, False, msg)
    ImageCategory.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_image_category(request):
    params = post_handle(request)
    sql = ImageCategory.objects.filter(name=params['name'])
    msg = validate_add_category_params(params, params['id'], sql)
    if msg:
        return res_handle(501, False, msg)
    ImageCategory.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_image_category(request):
    params = post_handle(request)
    sql = ImageCategory.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


def get_image_category_list(request):
    image_list = ImageCategory.objects.all().values(*['id', 'name', 'value', 'sort', 'createTime'])
    return res_handle(0, '查询成功', list(image_list))
