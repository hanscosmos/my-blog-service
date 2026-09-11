"""权限查询服务

权限模型：
    sys_user_role     用户 -> 角色（多对多）
    sys_role.is_super 超级管理员标记，固定由角色码 10000 的角色承担，拥有全部权限
    sys_authority_menu  角色 -> 菜单（多对多，覆盖目录 / 页面 / 按钮三种节点）
    menu.type='2' 页面节点代表「读权限」，决定侧边栏与路由可见性
    menu.type='3' 按钮节点，其 code 即操作权限码
"""

from config.choices import MENU_TYPE_BUTTON
from modules.authority.models import Menu, MenuAuthority, Role
from modules.user.models import UserAuthority


def get_user_role_ids(user_id):
    return list(
        UserAuthority.objects.filter(user=user_id, isForbidden=False).values_list(
            'role', flat=True
        )
    )


def get_user_roles(user_id):
    return list(Role.objects.filter(id__in=get_user_role_ids(user_id)))


def is_super_user(user_id):
    """是否拥有超级管理员角色"""
    return Role.objects.filter(id__in=get_user_role_ids(user_id), isSuper=True).exists()


def get_user_menu_ids(user_id):
    """当前用户被授予的菜单 id 集合；超管为全部菜单"""
    if is_super_user(user_id):
        return set(Menu.objects.values_list('id', flat=True))
    return set(
        MenuAuthority.objects.filter(
            role__in=get_user_role_ids(user_id), isForbidden=False
        ).values_list('menu', flat=True)
    )


def get_user_permission_codes(user_id):
    """当前用户的操作权限码集合（按钮节点）"""
    menu_ids = get_user_menu_ids(user_id)
    return list(
        Menu.objects.filter(id__in=menu_ids, type=MENU_TYPE_BUTTON).values_list(
            'code', flat=True
        )
    )


def has_permission(user_id, code):
    """是否拥有指定操作权限码"""
    if is_super_user(user_id):
        return True
    return Menu.objects.filter(
        id__in=get_user_menu_ids(user_id), type=MENU_TYPE_BUTTON, code=code
    ).exists()


def get_all_menu_routes():
    """全量受控路由（菜单中声明的页面路由 name）

    前端路由守卫据此判断「某个路由是否属于受菜单控制的页面」：
    不在此列表中的路由（详情页等）不做拦截，改由页面内的按钮权限控制入口。
    """
    return list(
        Menu.objects.exclude(type=MENU_TYPE_BUTTON)
        .exclude(route='')
        .values_list('route', flat=True)
    )


def with_ancestors(menu_ids):
    """补齐菜单 id 的祖先链

    只勾选子菜单而未勾选父级时，侧边栏树会因父节点缺失而挂载不上，
    因此按角色过滤菜单时必须把祖先节点一并补回来。
    """
    father_map = dict(Menu.objects.values_list('id', 'father'))
    result = set(menu_ids)
    for menu_id in list(menu_ids):
        father = father_map.get(menu_id)
        while father and father not in result:
            result.add(father)
            father = father_map.get(father)
    return result


def get_user_nav_menu_ids(user_id):
    """当前用户在侧边栏/路由中可见的菜单 id 集合（含补齐的祖先节点）"""
    if is_super_user(user_id):
        return set(Menu.objects.values_list('id', flat=True))
    return with_ancestors(get_user_menu_ids(user_id))
