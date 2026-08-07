from django.views.decorators.http import require_POST
from modules.article.models import ArticleCategory, Article
from modules.article.serializers.category import ArticleCategorySerializers
from modules.article.service.category import validate_add_article_category_params
from utils.response import res_handle
from utils.tools import post_handle, list_to_tree


@require_POST
def add_article_category(request):
    params = post_handle(request)
    msg = validate_add_article_category_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    ArticleCategory.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_article_category(request):
    params = post_handle(request)
    msg = validate_add_article_category_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    ArticleCategory.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_article_category(request):
    params = post_handle(request)
    is_exist = Article.objects.filter(category__in=params['ids']).exists()
    if is_exist:
        return res_handle(500, '该类别下存在文章', True)
    sql = ArticleCategory.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


def get_article_category_list(request):
    article_category_list = ArticleCategory.objects.all()
    return res_handle(0, '查询成功', list(article_category_list))


def get_all_article_category_tree(request):
    article_category_list = ArticleCategory.objects.all()
    new_article_category_list = ArticleCategorySerializers(instance=article_category_list, many=True)
    article_category_tree = list_to_tree(new_article_category_list.data, 'father', 'id')
    return res_handle(0, '查询成功', article_category_tree)
