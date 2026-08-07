from django.urls import path
from .views.role import *
from .views.menu import *


urlpatterns = [
    path('role/add', add_role, name='add_role'),
    path('role/edit', edit_role, name='edit_role'),
    path('role/delete', delete_role, name='delete_role'),
    path('role/list', get_role_list, name='get_role_list'),
    path('menu/add', add_menu, name='add_menu'),
    path('menu/edit', edit_menu, name='edit_menu'),
    path('menu/delete', delete_menu, name='delete_menu'),
    path('menu/tree/all', get_all_menu_tree, name='get_all_menu_tree'),
    path('menu/tree/nav', get_nav_menu_tree, name='get_nav_menu_tree'),
]
