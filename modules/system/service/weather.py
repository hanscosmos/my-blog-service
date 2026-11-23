import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

from modules.system.service.location import resolve_location

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
REQUEST_TIMEOUT = 8
CACHE_TTL = 60 * 15
STALE_CACHE_TTL = 60 * 60 * 12
TIMEZONE = 'Asia/Shanghai'

# WMO 天气码 -> 中文描述
WEATHER_CODE_MAP = {
    0: '晴',
    1: '大部晴朗',
    2: '多云',
    3: '阴',
    45: '雾',
    48: '雾凇',
    51: '毛毛雨',
    53: '毛毛雨',
    55: '毛毛雨',
    56: '冻毛毛雨',
    57: '冻毛毛雨',
    61: '小雨',
    63: '中雨',
    65: '大雨',
    66: '冻雨',
    67: '冻雨',
    71: '小雪',
    73: '中雪',
    75: '大雪',
    77: '米雪',
    80: '阵雨',
    81: '阵雨',
    82: '强阵雨',
    85: '阵雪',
    86: '阵雪',
    95: '雷阵雨',
    96: '雷暴伴冰雹',
    99: '雷暴伴冰雹',
}

logger = logging.getLogger(__name__)


def _to_number(value, digits=0):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    number = _to_number(value)
    return None if number is None else int(number)


def _weather_description(code):
    try:
        return WEATHER_CODE_MAP.get(int(code), '未知')
    except (TypeError, ValueError):
        return '未知'


def _daily_value(values, index):
    if not isinstance(values, list) or len(values) <= index:
        return None
    return values[index]


def _format_weather(payload):
    current = payload.get('current') or {}
    daily = payload.get('daily') or {}

    today_code = _daily_value(daily.get('weather_code'), 0)
    tomorrow_code = _daily_value(daily.get('weather_code'), 1)
    current_code = current.get('weather_code')

    return {
        'current': {
            'temperature': _to_int(current.get('temperature_2m')),
            'apparentTemperature': _to_int(current.get('apparent_temperature')),
            'humidity': _to_int(current.get('relative_humidity_2m')),
            'weatherCode': _to_int(current_code),
            'description': _weather_description(current_code),
            'windSpeed': _to_int(current.get('wind_speed_10m')),
            'isDay': bool(current.get('is_day', 1)),
        },
        'today': {
            'min': _to_int(_daily_value(daily.get('temperature_2m_min'), 0)),
            'max': _to_int(_daily_value(daily.get('temperature_2m_max'), 0)),
            'weatherCode': _to_int(today_code),
            'description': _weather_description(today_code),
            'rainProbability': _to_int(
                _daily_value(daily.get('precipitation_probability_max'), 0)
            ),
        },
        'tomorrow': {
            'min': _to_int(_daily_value(daily.get('temperature_2m_min'), 1)),
            'max': _to_int(_daily_value(daily.get('temperature_2m_max'), 1)),
            'weatherCode': _to_int(tomorrow_code),
            'description': _weather_description(tomorrow_code),
            'rainProbability': _to_int(
                _daily_value(daily.get('precipitation_probability_max'), 1)
            ),
        },
    }


def _fetch_weather(latitude, longitude):
    resp = requests.get(
        OPEN_METEO_URL,
        params={
            'latitude': latitude,
            'longitude': longitude,
            'timezone': TIMEZONE,
            'forecast_days': 2,
            'wind_speed_unit': 'kmh',
            'current': ','.join(
                [
                    'temperature_2m',
                    'relative_humidity_2m',
                    'apparent_temperature',
                    'weather_code',
                    'wind_speed_10m',
                    'is_day',
                ]
            ),
            'daily': ','.join(
                [
                    'weather_code',
                    'temperature_2m_max',
                    'temperature_2m_min',
                    'precipitation_probability_max',
                ]
            ),
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data.get('current'), dict):
        raise ValueError('天气数据为空')
    return data


def get_weather_data(latitude=None, longitude=None, client_ip=None, force=False):
    location = resolve_location(latitude, longitude, client_ip)
    now = datetime.now(ZoneInfo(TIMEZONE))

    result = {
        'location': location,
        'updatedAt': now.strftime('%Y-%m-%d %H:%M'),
        'current': None,
        'today': None,
        'tomorrow': None,
        'stale': False,
        'available': False,
    }

    if not location.get('available'):
        return result

    lat = location['latitude']
    lon = location['longitude']
    cache_key = f'sys:weather:{lat:.2f}:{lon:.2f}'
    stale_cache_key = f'sys:weather:last:{lat:.2f}:{lon:.2f}'

    if not force:
        cached = cache.get(cache_key)
        if cached:
            return {**result, **cached, 'location': location, 'available': True}

    try:
        weather = _format_weather(_fetch_weather(lat, lon))
        weather['updatedAt'] = now.strftime('%Y-%m-%d %H:%M')
        cache.set(cache_key, weather, CACHE_TTL)
        cache.set(stale_cache_key, weather, STALE_CACHE_TTL)
        return {**result, **weather, 'location': location, 'available': True}
    except Exception as exc:
        logger.warning('天气数据获取失败: %s', exc)
        stale = cache.get(stale_cache_key)
        if stale:
            return {
                **result,
                **stale,
                'location': location,
                'available': True,
                'stale': True,
            }
        return result
