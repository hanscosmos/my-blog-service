from django.views.decorators.http import require_POST

from modules.system.service.holding import (
    get_holding_history,
    get_holding_remind_status,
    record_holding_snapshot,
)
from utils.response import res_handle
from .fund import _get_super_user_id


@require_POST
def get_holding_history_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        data = get_holding_history(user_id)
    except Exception:
        return res_handle(500, '持仓历史获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def get_holding_remind_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        data = get_holding_remind_status(user_id)
    except Exception:
        return res_handle(500, '持仓提醒获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)


@require_POST
def record_holding_snapshot_view(request):
    user_id, error = _get_super_user_id(request)
    if error:
        return error
    try:
        record_holding_snapshot(user_id)
    except Exception:
        return res_handle(500, '持仓快照记录失败，请稍后重试', False)
    return res_handle(0, '记录成功', True)
