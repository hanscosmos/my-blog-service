import hashlib
import ipaddress
import logging

import requests
from django.core.cache import cache

REQUEST_TIMEOUT = 6
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'
IPAPI_CO_URL = 'https://ipapi.co/{ip}/json/'
IPAPI_CO_SELF_URL = 'https://ipapi.co/json/'
IP_API_URL = 'http://ip-api.com/json/{ip}'
IP_API_SELF_URL = 'http://ip-api.com/json/'
USER_AGENT = 'my-blog-admin/1.0 (personal blog backend)'

REVERSE_CACHE_TTL = 60 * 60 * 24 * 30
IP_CACHE_TTL = 60 * 60 * 24
SERVER_IP_CACHE_TTL = 60 * 60 * 24 * 7

CITY_SUFFIXES = ('市', '自治州', '地区', '盟')
COUNTY_SUFFIXES = ('区', '县', '旗')

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """按代理头优先取客户端真实 IP"""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        ip = forwarded.split(',')[0].strip()
        if ip:
            return ip
    real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
    if real_ip:
        return real_ip
    return request.META.get('REMOTE_ADDR', '').strip()


def is_private_ip(ip):
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
    )


def _format_nominatim(payload):
    """
    Nominatim 的 address 字段对国内地址经常把「区」放进 city、
    把「街道」放进 county，这里统一按 display_name 的行政层级解析，
    优先得到「市 + 区/县」。
    """
    address = payload.get('address') or {}
    display_name = (payload.get('display_name') or '').strip()
    country = (address.get('country') or '').strip()

    parts = [part.strip() for part in display_name.split(',') if part.strip()]
    if country and parts and parts[-1] == country:
        parts = parts[:-1]

    city = ''
    county = ''
    city_indexes = [
        index for index, part in enumerate(parts) if part.endswith(CITY_SUFFIXES)
    ]
    if city_indexes:
        # 取最靠后的「市」作为地级市；多个「市」时前一个是县级市
        city = parts[city_indexes[-1]]
        if len(city_indexes) > 1:
            county = parts[city_indexes[0]]
        else:
            for part in reversed(parts[: city_indexes[-1]]):
                if part.endswith(COUNTY_SUFFIXES):
                    county = part
                    break

    if not city:
        city = (
            address.get('city')
            or address.get('municipality')
            or address.get('state')
            or ''
        ).strip()
    if not county:
        candidate = (
            address.get('county')
            or address.get('city_district')
            or address.get('district')
            or ''
        ).strip()
        if candidate and candidate != city and candidate.endswith(COUNTY_SUFFIXES):
            county = candidate

    if not city and not county:
        return {}

    display_parts = []
    for part in [city, county]:
        if part and part not in display_parts:
            display_parts.append(part)

    return {
        'city': city,
        'county': county,
        'displayName': ' '.join(display_parts) or display_name,
    }


def reverse_geocode(latitude, longitude):
    """把经纬度解析成城市/区县，坐标按 2 位小数缓存 30 天"""
    cache_key = f'sys:geo:reverse:{latitude:.2f}:{longitude:.2f}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                'format': 'jsonv2',
                'lat': latitude,
                'lon': longitude,
                'zoom': 14,
                'addressdetails': 1,
                'accept-language': 'zh-CN,zh;q=0.9',
            },
            headers={
                'User-Agent': USER_AGENT,
                'Accept-Language': 'zh-CN,zh;q=0.9',
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = _format_nominatim(resp.json())
    except Exception as exc:
        logger.warning('逆地理编码失败: %s', exc)
        return {}

    if data:
        cache.set(cache_key, data, REVERSE_CACHE_TTL)
    return data


def _fetch_ipapi_co(ip=None):
    url = IPAPI_CO_URL.format(ip=ip) if ip else IPAPI_CO_SELF_URL
    try:
        resp = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning('ipapi.co 定位失败: %s', exc)
        return None

    if not isinstance(payload, dict) or payload.get('error'):
        return None
    try:
        latitude = round(float(payload.get('latitude')), 2)
        longitude = round(float(payload.get('longitude')), 2)
    except (TypeError, ValueError):
        return None

    city = (payload.get('city') or payload.get('region') or '').strip()
    return {
        'city': city,
        'county': '',
        'displayName': city,
        'latitude': latitude,
        'longitude': longitude,
    }


def _fetch_ip_api(ip=None):
    url = IP_API_URL.format(ip=ip) if ip else IP_API_SELF_URL
    try:
        resp = requests.get(
            url,
            params={
                'lang': 'zh-CN',
                'fields': 'status,message,country,regionName,city,lat,lon',
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning('ip-api.com 定位失败: %s', exc)
        return None

    if not isinstance(payload, dict) or payload.get('status') != 'success':
        return None
    try:
        latitude = round(float(payload.get('lat')), 2)
        longitude = round(float(payload.get('lon')), 2)
    except (TypeError, ValueError):
        return None

    city = (payload.get('city') or payload.get('regionName') or '').strip()
    return {
        'city': city,
        'county': '',
        'displayName': city,
        'latitude': latitude,
        'longitude': longitude,
    }


def get_ip_location(ip=None):
    """按客户端 IP 定位；ip 为空时定位服务器自身出网 IP"""
    if ip and is_private_ip(ip):
        return None

    if ip:
        cache_key = f'sys:geo:ip:{hashlib.md5(ip.encode("utf-8")).hexdigest()}'
        ttl = IP_CACHE_TTL
    else:
        cache_key = 'sys:geo:ip:server'
        ttl = SERVER_IP_CACHE_TTL

    cached = cache.get(cache_key)
    if cached:
        return cached

    data = _fetch_ipapi_co(ip) or _fetch_ip_api(ip)
    if data:
        cache.set(cache_key, data, ttl)
    return data


def resolve_location(latitude=None, longitude=None, client_ip=None):
    """
    定位优先级：浏览器经纬度 -> 客户端 IP -> 服务器出网 IP
    返回统一结构，available 为 False 表示全部失败
    """
    empty = {
        'city': '',
        'county': '',
        'displayName': '',
        'latitude': None,
        'longitude': None,
        'source': 'none',
        'available': False,
    }

    if latitude is not None and longitude is not None:
        latitude = round(float(latitude), 2)
        longitude = round(float(longitude), 2)
        geo = reverse_geocode(latitude, longitude)
        source = 'gps'

        if not geo:
            # 逆地理编码失败时仍用 GPS 坐标取天气，不再用 IP 城市以免位置错配
            geo = {'city': '', 'county': '', 'displayName': '当前位置'}

        return {
            'city': geo.get('city', ''),
            'county': geo.get('county', ''),
            'displayName': geo.get('displayName') or '当前位置',
            'latitude': latitude,
            'longitude': longitude,
            'source': source,
            'available': True,
        }

    ip_info = None
    if client_ip and not is_private_ip(client_ip):
        ip_info = get_ip_location(client_ip)
    source = 'ip' if ip_info else 'server'
    if not ip_info:
        ip_info = get_ip_location()
    if not ip_info:
        return empty

    city = ip_info.get('city', '')
    return {
        'city': city,
        'county': ip_info.get('county', ''),
        'displayName': city or '当前位置',
        'latitude': ip_info.get('latitude'),
        'longitude': ip_info.get('longitude'),
        'source': source,
        'available': ip_info.get('latitude') is not None,
    }
