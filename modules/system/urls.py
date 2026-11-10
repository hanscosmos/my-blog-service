from django.urls import path
from .views.other import *
from .views.dictionary import *
from .views.updateLog import *
from .views.market import *
from .views.fund import *

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
    path('market/overview', get_market_overview, name='get_market_overview'),
    path('market/news', get_market_news, name='get_market_news'),
    path('market/hot', get_market_hot, name='get_market_hot'),
    path('market/trend', get_market_trend, name='get_market_trend'),
    path('market/fund/portfolio', get_fund_portfolio, name='get_fund_portfolio'),
    path('market/fund/search', search_market_fund, name='search_market_fund'),
    path('market/fund/holding/save', save_fund_holding_view, name='save_fund_holding'),
    path('market/fund/holding/delete', delete_fund_holding_view, name='delete_fund_holding'),

]
