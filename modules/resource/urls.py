from django.urls import path
from .views.icon import *
from .views.image import *


urlpatterns = [
    path('icon/add', add_icon, name='add_icon'),
    path('icon/edit', edit_icon, name='edit_icon'),
    path('icon/delete', delete_icon, name='delete_icon'),
    path('icon/list', get_icon_list, name='get_icon_list'),
    path('icon/category/add', add_icon_category, name='add_icon_category'),
    path('icon/category/edit', edit_icon_category, name='edit_icon_category'),
    path('icon/category/delete', delete_icon_category, name='delete_icon_category'),
    path('icon/category/list', get_icon_category_list, name='get_icon_category_list'),
    path('image/add', add_image, name='add_image'),
    path('image/edit', edit_image, name='edit_image'),
    path('image/delete', delete_image, name='delete_image'),
    path('image/list', get_image_list, name='get_image_list'),
    path('image/category/add', add_image_category, name='add_image_category'),
    path('image/category/edit', edit_image_category, name='edit_image_category'),
    path('image/category/delete', delete_image_category, name='delete_image_category'),
    path('image/category/list', get_image_category_list, name='get_image_category_list'),
]
