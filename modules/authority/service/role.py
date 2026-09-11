from config.choices import SUPER_ROLE_CODE
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
    if code == SUPER_ROLE_CODE:
        # 超级管理员角色为系统内置，不允许通过接口新增或改写
        return '超级管理员角色为系统内置，不可新增或修改'
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


def validate_edit_role_params(params, role_id):
    """在基础校验之上，保护内置的超级管理员角色"""
    if not Role.objects.filter(id=role_id).exists():
        return '角色不存在'
    role = Role.objects.get(id=role_id)
    if role.isSuper:
        return '超级管理员角色不可修改'
    return validate_add_role_params(params, role_id)


def validate_delete_role_params(ids):
    msg: str = ''
    if not ids:
        msg = '请选择要删除的角色'
    elif Role.objects.filter(id__in=ids, isSuper=True).exists():
        msg = '超级管理员角色不可删除'
    return msg


def validate_set_role_menu_params(role_id, menu_ids):
    msg: str = ''
    role = Role.objects.filter(id=role_id).first() if role_id else None
    if not role_id:
        msg = '请选择要授权的角色'
    elif not role:
        msg = '角色不存在'
    elif role.isSuper:
        # 超管默认拥有全部权限，无需也不允许单独分配
        msg = '超级管理员默认拥有全部权限，无需分配'
    elif not isinstance(menu_ids, list):
        msg = '菜单参数格式错误'

    return msg


