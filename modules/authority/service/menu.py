from modules.authority.models import Menu


def validate_add_menu_params(params, menu_id):
    msg: str = ''
    name, code, father = params['name'], params['code'], params['father']
    if not name:
        msg = '菜单名不得为空'
    if not code:
        msg = '菜单码不得为空'
    if len(name) < 2 or len(name) > 10:
        msg = '菜单名长度为2-10'
    name_sql = Menu.objects.filter(name=name, father=father)
    code_sql = Menu.objects.filter(code=code)
    if menu_id:
        is_name_exist = name_sql.exclude(id=menu_id).exists()
        is_code_exist = code_sql.exclude(id=menu_id).exists()
    else:
        is_name_exist = name_sql.exists()
        is_code_exist = code_sql.exists()
    if is_name_exist:
        msg = '同级菜单名已存在'
    if is_code_exist:
        msg = '菜单码已存在'

    return msg


