from modules.system.models import Dictionary


def validate_add_dict_params(params, dict_id):
    msg: str = ''
    key, value, code = params['key'], params['value'], params['code']
    if not key:
        msg = '字典key不得为空'
    if not value:
        msg = '字典value不得为空'
    if not code:
        msg = '字典分类不得为空'
    if len(key) < 1 or len(key) > 64:
        msg = '字典key长度为1-64'
    if len(value) < 1 or len(value) > 64:
        msg = '字典value长度为1-64'
    key_sql = Dictionary.objects.filter(key=key, code=code)
    value_sql = Dictionary.objects.filter(value=value, code=code)
    if not dict_id:
        is_key_exist = key_sql.exists()
        is_value_exist = value_sql.exists()
    else:
        is_key_exist = key_sql.exclude(id=dict_id).exists()
        is_value_exist = value_sql.exclude(id=dict_id).exists()
    if is_key_exist:
        msg = '当前分类字典key已存在'
    if is_value_exist:
        msg = '当前分类字典value已存在'
    return msg
