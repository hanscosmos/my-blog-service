from django.views.decorators.http import require_POST
from modules.authority.models import Menu
from modules.authority.serializers.menu import MenuSerializers
from modules.authority.service.menu import validate_add_menu_params
from utils.response import res_handle
from utils.tools import post_handle, list_to_tree


@require_POST
def add_menu(request):
    params = post_handle(request)
    msg = validate_add_menu_params(params, None)
    if msg:
        return res_handle(501, False, msg)
    Menu.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_menu(request):
    params = post_handle(request)
    msg = validate_add_menu_params(params, params['id'])
    if msg:
        return res_handle(501, msg, False)
    Menu.objects.filter(id=params['id']).update(**params)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_menu(request):
    params = post_handle(request)
    sql = Menu.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


def get_menu_list(request):
    menu_list = Menu.objects.all()
    return res_handle(0, '查询成功', list(menu_list))


def get_all_menu_tree(request):
    menu_list = Menu.objects.all()
    new_menu_list = MenuSerializers(instance=menu_list, many=True)
    # print('aaa',list(new_menu_list.data))
    menu_tree = list_to_tree(new_menu_list.data, 'father', 'id')
    return res_handle(0, '查询成功', menu_tree)


def get_nav_menu_tree(request):
    menu_list = list(Menu.objects.filter(type__in=['1', '2']))
    menu_tree = list_to_tree(menu_list, 'father', 'id')
    return res_handle(0, '查询成功', menu_tree)
