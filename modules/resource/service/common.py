def validate_add_category_params(params, category_id, sql):
    msg: str = ''
    name = params['name']
    if not name:
        msg = '类别名不得为空'
    if len(name) < 2 or len(name) > 10:
        msg = '类别名长度为2-10'
    if not category_id:
        is_name_exist = sql.exists()
    else:
        is_name_exist = sql.exclude(id=category_id).exists()
    if is_name_exist:
        msg = '类别名已存在'
    return msg
