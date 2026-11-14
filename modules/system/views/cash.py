from django.views.decorators.http import require_POST

from modules.system.service.cash import (
    delete_cash_holdings,
    get_cash_portfolio_data,
    save_cash_holding,
)
from utils.response import res_handle
from utils.tools import post_handle
from .fund import _get_super_user_id


@require_POST
def get_cash_portfolio(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    try:
        data = get_cash_portfolio_data(user_id, bool(params.get('force')))
    except Exception:
        return res_handle(500, '现金存款获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def save_cash_holding_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        save_cash_holding(user_id, params)
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '资产保存失败，请稍后重试', False)
    return res_handle(0, '保存成功', True)


@require_POST
def delete_cash_holding_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        delete_cash_holdings(user_id, params.get('ids'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '资产删除失败，请稍后重试', False)
    return res_handle(0, '删除成功', True)
