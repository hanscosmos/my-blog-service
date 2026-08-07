def validate_add_article_params(params):
    msg: str = ''
    title, content = params['title'], params['content']
    if not title:
        msg = '文章标题不得为空'
    if not content:
        msg = '文章内容不得为空'
    if len(title) < 2 or len(title) > 32:
        msg = '文章标题长度为2-32'
    return msg


