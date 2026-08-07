from modules.article.models import ArticleCategory


def validate_add_article_category_params(params, article_category_id):
    msg: str = ''
    name, alias = params['name'], params['alias']
    if not name:
        msg = '文章类别名不得为空'
    if not alias:
        msg = '文章类别别名不得为空'
    if len(name) < 2 or len(name) > 10:
        msg = '文章类别名长度为2-10'
    name_sql = ArticleCategory.objects.filter(name=name)
    alias_sql = ArticleCategory.objects.filter(alias=alias)
    if article_category_id:
        is_name_exist = name_sql.exclude(id=article_category_id).exists()
        is_alias_exist = alias_sql.exclude(id=article_category_id).exists()
    else:
        is_name_exist = name_sql.exists()
        is_alias_exist = alias_sql.exists()
    if is_name_exist:
        msg = '文章类别名已存在'
    if is_alias_exist:
        msg = '文章类别别名已存在'

    return msg


