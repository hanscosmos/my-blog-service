from django.urls import path
from .views import *
from modules.article.views.article import *
from modules.article.views.category import *
from modules.client.views import *


urlpatterns = [
    path('article/detail', get_client_article_detail, name="get_article_detail"),
    path('article/list', get_client_article_list, name="get_article_list"),
    path('article/hot', get_hot_article_list, name="get_hot_article_list"),
    path('article/category/tree', get_all_article_category_tree, name="get_all_article_category_tree"),
    path('article/read/stat', get_article_read_stat, name="get_article_read_stat"),
    path('article/stat/category', get_article_count_by_category, name="get_article_count_by_category"),
    path('article/stat/tag', get_article_count_by_tag, name="get_article_count_by_tag"),
    path('article/stat/column', get_article_count_by_column, name="get_article_count_by_column"),

]
