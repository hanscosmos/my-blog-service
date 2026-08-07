from django.views.decorators.http import require_POST

from modules.article.models import ArticleTag
from modules.article.service.tag import validate_add_article_tag_params
from utils.response import res_handle, res_limit
from utils.tools import post_handle


@require_POST
def add_tag(request):
    params = post_handle(request)
    msg = validate_add_article_tag_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    ArticleTag.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_tag(request):
    params = post_handle(request)
    msg = validate_add_article_tag_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    ArticleTag.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_tag(request):
    params = post_handle(request)
    sql = ArticleTag.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_tag_list(request):
    params = post_handle(request)
    sql = ArticleTag.objects.filter(name__contains=params['name']).values(
        *['id', 'name', 'alias', 'color', 'sort', 'description', 'createTime'])
    if params['name']:
        sql = sql.filter(name__contains=params['name'])
    return res_limit(params, sql)
