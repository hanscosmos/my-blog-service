from django.views.decorators.http import require_POST

from modules.article.models import ArticleColumn
from modules.article.service.column import validate_add_article_column_params
from utils.auth import get_user_id
from utils.response import res_handle, res_limit
from utils.tools import post_handle


@require_POST
def add_column(request):
    params = post_handle(request)
    params['user'] = get_user_id(request)
    msg = validate_add_article_column_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    ArticleColumn.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_column(request):
    params = post_handle(request)
    params['user'] = get_user_id(request)
    msg = validate_add_article_column_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    ArticleColumn.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_column(request):
    params = post_handle(request)
    sql = ArticleColumn.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_column_list(request):
    params = post_handle(request)
    sql = ArticleColumn.objects.filter(name__contains=params['name']).values(
        *['id', 'name', 'cover', 'sort', 'description', 'createTime'])
    if params['name']:
        sql = sql.filter(name__contains=params['name'])
    return res_limit(params, sql)
