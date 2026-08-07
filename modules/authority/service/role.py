from modules.authority.models import Role


def validate_add_role_params(params, role_id):
    msg: str = ''
    name, code = params['name'], params['code']
    if not name:
        msg = '角色名不得为空'
    if not code:
        msg = '角色码不得为空'
    if len(name) < 2 or len(name) > 10:
        msg = '角色名长度为2-10'
    name_sql = Role.objects.filter(name=name)
    code_sql = Role.objects.filter(code=code)
    if role_id:
        is_name_exist = name_sql.exclude(id=role_id).exists()
        is_code_exist = code_sql.exclude(id=role_id).exists()
    else:
        is_name_exist = name_sql.exists()
        is_code_exist = code_sql.exists()
    if is_name_exist:
        msg = '角色名已存在'
    if is_code_exist:
        msg = '角色码已存在'

    return msg


