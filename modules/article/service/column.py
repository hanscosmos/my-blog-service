from modules.article.models import ArticleColumn


# 此方法后续要加上用户判断
def validate_add_article_column_params(params, article_column_id):
    msg: str = ''
    name = params['name']
    if not name:
        msg = '文章专栏名不得为空'
    if len(name) < 2 or len(name) > 16:
        msg = '文章专栏名长度为2-16'
    name_sql = ArticleColumn.objects.filter(name=name)
    if article_column_id:
        is_name_exist = name_sql.exclude(id=article_column_id).exists()
    else:
        is_name_exist = name_sql.exists()
    if is_name_exist:
        msg = '文章专栏名已存在'

    return msg


