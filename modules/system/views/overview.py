from django.views.decorators.http import require_POST

from modules.system.service.hardware import get_hardware_data
from modules.system.service.location import get_client_ip
from modules.system.service.weather import get_weather_data
from utils.response import res_handle
from utils.tools import post_handle


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _valid_coordinate(latitude, longitude):
    if latitude is None or longitude is None:
        return None, None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None, None
    return latitude, longitude


@require_POST
def get_weather_overview(request):
    try:
        params = post_handle(request)
    except Exception:
        params = {}

    latitude, longitude = _valid_coordinate(
        _to_float(params.get('latitude')),
        _to_float(params.get('longitude')),
    )
    data = get_weather_data(
        latitude,
        longitude,
        get_client_ip(request),
        bool(params.get('force')),
    )
    return res_handle(0, '查询成功', data)


@require_POST
def get_hardware_overview(request):
    try:
        params = post_handle(request)
    except Exception:
        params = {}
    return res_handle(0, '查询成功', get_hardware_data(bool(params.get('force'))))
