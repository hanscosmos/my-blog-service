from django.urls import path
from .views.other import *
from .views.dictionary import *
from .views.updateLog import *

urlpatterns = [
    path('file/upload', upload_file, name='upload_file'),
    path('dict/list', get_dictionary_list, name='get_dictionary_list'),
    path('dict/add', add_dictionary, name='add_dictionary'),
    path('dict/edit', edit_dictionary, name='edit_dictionary'),
    path('dict/delete', delete_dictionary, name='delete_dictionary'),
    path('dict/change/status', change_dictionary_status, name='change_dictionary_status'),
    path('dict/list/code', get_available_dictionary_list, name='get_available_dictionary_list'),
    path('updateLog/list', get_update_log_list, name='get_update_log_list'),
    path('updateLog/add', add_update_log, name='add_update_log'),
    path('updateLog/edit', edit_update_log, name='edit_update_log'),
    path('updateLog/delete', delete_update_log, name='delete_update_log'),
    path('stat', get_sys_stat, name='get_sys_stat'),
    path('self/stat', get_self_stats, name='get_self_stats'),

]
