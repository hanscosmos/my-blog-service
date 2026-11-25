from django.views.decorators.http import require_POST

from modules.system.service.physical import (
    delete_physical_assets,
    get_physical_portfolio_data,
    save_physical_asset,
)
from utils.response import res_handle
from utils.tools import post_handle
from .fund import _get_super_user_id


@require_POST
def get_physical_portfolio(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        data = get_physical_portfolio_data(user_id)
    except Exception:
        return res_handle(500, '实物资产获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def save_physical_asset_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        save_physical_asset(user_id, params)
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '实物资产保存失败，请稍后重试', False)
    return res_handle(0, '保存成功', True)


@require_POST
def delete_physical_asset_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        params = post_handle(request)
    except Exception:
        return res_handle(501, '参数解析失败', False)
    try:
        delete_physical_assets(user_id, params.get('ids'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    except Exception:
        return res_handle(500, '实物资产删除失败，请稍后重试', False)
    return res_handle(0, '删除成功', True)
