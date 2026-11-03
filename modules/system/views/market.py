from django.views.decorators.http import require_POST

from modules.system.service.market import get_market_overview_data
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
