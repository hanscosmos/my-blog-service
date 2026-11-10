from django.views.decorators.http import require_POST

from modules.authority.service.permission import is_super_user
from modules.system.service.fund import (
    delete_fund_holdings,
    get_fund_portfolio_data,
    save_fund_holding,
    search_funds,
)
from utils.auth import get_user_id
from utils.response import res_handle
from utils.tools import post_handle


def _get_super_user_id(request):
    user_id = get_user_id(request)
    if not user_id:
        return None, res_handle(401, '请先登录', None)
    if not is_super_user(user_id):
        return None, res_handle(403, '该功能仅超级管理员可用', None)
    return user_id, None


@require_POST
def get_fund_portfolio(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    try:
        data = get_fund_portfolio_data(user_id, bool(params.get('force')))
    except Exception:
        return res_handle(500, '基金持仓获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def search_market_fund(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    keyword = str(params.get('keyword') or '').strip()
    if not keyword:
        return res_handle(0, '查询成功', [])
    try:
        data = search_funds(keyword)
    except Exception:
        return res_handle(500, '基金搜索失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def save_fund_holding_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        save_fund_holding(user_id, params)
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '持仓保存失败，请稍后重试', False)
    return res_handle(0, '保存成功', True)


@require_POST
def delete_fund_holding_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        delete_fund_holdings(user_id, params.get('ids'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '持仓删除失败，请稍后重试', False)
    return res_handle(0, '删除成功', True)
