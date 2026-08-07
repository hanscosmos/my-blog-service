from django.urls import path
from .views.category import *
from .views.tag import *
from .views.article import *
from .views.column import *


urlpatterns = [
    path('add', add_article, name="add_article"),
    path('update', edit_article, name="edit_article"),
    path('delete', delete_article, name="delete_article"),
    path('list', get_article_list, name="get_article_list"),
    path('hot', get_hot_article_list, name="get_hot_article_list"),
    path('detail', get_article_detail, name="get_article_detail"),
    path('publish/trend', get_article_publish_stat, name="get_article_publish_stat"),
    path('read/stat', get_article_read_stat, name="get_article_read_stat"),
    path('category/add', add_article_category, name='add_article_category'),
    path('category/edit', edit_article_category, name='edit_article_category'),
    path('category/delete', delete_article_category, name='delete_article_category'),
    path('category/list', get_article_category_list, name='get_article_category_list'),
    path('category/tree', get_all_article_category_tree, name='get_all_article_category_tree'),
    path('tag/add', add_tag, name='add_tag'),
    path('tag/edit', edit_tag, name='edit_tag'),
    path('tag/delete', delete_tag, name='delete_tag'),
    path('tag/list', get_tag_list, name='get_tag_list'),
    path('column/add', add_column, name='add_column'),
    path('column/edit', edit_column, name='edit_column'),
    path('column/delete', delete_column, name='delete_column'),
    path('column/list', get_column_list, name='get_column_list'),
]
