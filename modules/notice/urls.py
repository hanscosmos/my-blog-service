from django.urls import path

from .views import *

urlpatterns = [
    path('list', get_notice_list, name='get_notice_list'),
    path('unread/count', get_notice_unread_count, name='get_notice_unread_count'),
    path('read/all', read_all_notice, name='read_all_notice'),
    path('read', read_notice, name='read_notice'),
]
