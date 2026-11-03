from django.views.decorators.http import require_POST

from modules.system.service.market import (
    TREND_PERIODS,
    get_market_overview_data,
    get_market_trend_data,
)
from utils.response import res_handle
from utils.tools import post_handle


@require_POST
def get_market_overview(request):
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    data = get_market_overview_data(bool(params.get('force')))
    return res_handle(0, '查询成功', data)


@require_POST
def get_market_trend(request):
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    key = params.get('key')
    period = params.get('period', 'minute')
    if not key:
        return res_handle(400, '缺少行情标识')
    if period not in TREND_PERIODS:
        return res_handle(400, '不支持的周期')
    try:
        data = get_market_trend_data(key, period, bool(params.get('force')))
    except KeyError:
        return res_handle(400, '该行情暂不支持趋势查看')
    except Exception:
        return res_handle(500, '趋势数据获取失败，请稍后重试')
    return res_handle(0, '查询成功', data)
