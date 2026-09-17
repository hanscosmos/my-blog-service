from django.urls import path

from .views import *

urlpatterns = [
    path('list', get_admin_comment_list, name='get_admin_comment_list'),
    path('delete', delete_admin_comment, name='delete_admin_comment'),
    path('forbid-user', forbid_comment_user, name='forbid_comment_user'),
]
