from modules.authority.service.permission import (
    get_all_menu_routes,
    get_user_permission_codes,
    get_user_roles,
    is_super_user,
)
from utils.auth import get_user_id
from utils.response import res_handle


def get_self_permission(request):
    """当前登录用户的角色、操作权限码与受控路由，供前端按钮级 / 路由级鉴权使用"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '您未登录，没有权限访问该接口')
    roles = get_user_roles(user_id)
    data = {
        'isSuper': is_super_user(user_id),
        'roles': [
            {'id': str(role.id), 'name': role.name, 'code': role.code} for role in roles
        ],
        'codes': get_user_permission_codes(user_id),
        'menuRoutes': get_all_menu_routes(),
    }
    return res_handle(0, '查询成功', data)
