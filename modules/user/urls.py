from django.urls import path
from .views.user import *
from .views.task import *

urlpatterns = [
    path('list', get_user_list, name='get_user_list'),
    path('login', user_login_admin_system, name='user_login_admin_system'),
    path('refresh', user_refresh_token, name='user_refresh_token'),
    path('add', add_user_by_admin, name='add_user_by_admin'),
    path('set/role', set_user_role, name='set_user_role'),
    path('valid/code', get_valid_code, name='get_valid_code'),
    path('update/self', update_self_info, name='update_self_info'),
    path('get/self', get_self_info, name='get_self_info'),
    path('stats', get_user_stats, name='get_user_stats'),
    path('article/list', get_user_article_list, name='get_self_article_list'),
    path('activity/list', get_self_activity_log, name="get_self_activity_log"),
    path('activity/delete', delete_user_activity, name='delete_user_activity'),
    path('task/list', get_user_task_list, name='get_user_task_list'),
    path('task/panel/list', get_user_task_panel_list, name='get_user_task_panel_list'),
    path('task/recent/list', get_user__recent_task_list, name='get_user__recent_task_list'),
    path('task/remind/list', get_user_task_remind_list, name='get_user_task_remind_list'),
    path('task/add', add_user_task, name='add_user_task'),
    path('task/update', edit_user_task, name='edit_user_task'),
    path('task/delete', delete_user_task, name='delete_user_task'),
    path('task/score/stat', get_person_score_stats, name='get_person_score_stats'),
]
