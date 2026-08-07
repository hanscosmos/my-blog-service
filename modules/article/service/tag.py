from modules.article.models import ArticleTag


def validate_add_article_tag_params(params, article_tag_id):
    msg: str = ''
    name, alias = params['name'], params['alias']
    if not name:
        msg = '文章标签名不得为空'
    if not alias:
        msg = '文章标签别名不得为空'
    if len(name) < 2 or len(name) > 10:
        msg = '文章标签名长度为2-10'
    name_sql = ArticleTag.objects.filter(name=name)
    alias_sql = ArticleTag.objects.filter(alias=alias)
    if article_tag_id:
        is_name_exist = name_sql.exclude(id=article_tag_id).exists()
        is_alias_exist = alias_sql.exclude(id=article_tag_id).exists()
    else:
        is_name_exist = name_sql.exists()
        is_alias_exist = alias_sql.exists()
    if is_name_exist:
        msg = '文章标签名已存在'
    if is_alias_exist:
        msg = '文章标签别名已存在'

    return msg


