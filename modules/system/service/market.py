import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

CACHE_KEY = 'market:overview'
STALE_CACHE_KEY = 'market:overview:stale'
CACHE_TTL = 30
STALE_CACHE_TTL = 600
REQUEST_TIMEOUT = 5

CN_TZ = ZoneInfo('Asia/Shanghai')
US_TZ = ZoneInfo('America/New_York')

TENCENT_URL = 'https://qt.gtimg.cn/q='
SINA_URL = 'https://hq.sinajs.cn/list=fx_susdcnh'
CFETS_URL = 'https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/fx/ccpr.json'

CN_ITEMS = [('sh000300', '沪深300'), ('sz399006', '创业板指'), ('sh000688', '科创50')]
US_ITEMS = [('usINX', '标普500'), ('usNDX', '纳斯达克100')]
COMMODITY_ITEMS = [
    ('hf_XAU', '伦敦金'),
    ('hf_XAG', '伦敦银'),
    ('hf_OIL', '布伦特原油'),
    ('hf_CL', 'NYMEX原油'),
]
TENCENT_CODES = [code for code, _ in CN_ITEMS + US_ITEMS + COMMODITY_ITEMS]

STATUS_TEXT = {
    'open': '交易中',
    'break': '午间休市',
    'closed': '已收盘',
    'holiday': '休市',
}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _precision(raw_value, max_precision=4):
    if not isinstance(raw_value, str) or '.' not in raw_value:
        return 2
    return min(len(raw_value.split('.')[1]), max_precision)


def _format_quote_time(raw):
    raw = (raw or '').strip()
    if len(raw) == 14 and raw.isdigit():
        return f'{raw[:4]}-{raw[4:6]}-{raw[6:8]} {raw[8:10]}:{raw[10:12]}:{raw[12:14]}'
    return raw


def _format_cfets_time(raw):
    try:
        return datetime.strptime(raw.strip(), '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return raw


def _parse_tencent_quote(raw):
    if ',' in raw and '~' not in raw:
        fields = raw.split(',')
        if len(fields) < 14:
            return None
        raw_price = fields[0].strip()
        price = _to_float(raw_price)
        prev_close = _to_float(fields[7])
        precision = _precision(raw_price)
        change = None
        if price is not None and prev_close not in (None, 0):
            change = round(price - prev_close, precision)
        quote_date = fields[12].strip()
        return {
            'price': price,
            'change': change,
            'changePercent': _to_float(fields[1]),
            'precision': precision,
            'quoteTime': f'{quote_date} {fields[6].strip()}'.strip(),
            'quoteDate': quote_date,
        }

    fields = raw.split('~')
    if len(fields) < 33:
        return None
    raw_price = fields[3].strip()
    quote_time = _format_quote_time(fields[30])
    return {
        'price': _to_float(raw_price),
        'change': _to_float(fields[31]),
        'changePercent': _to_float(fields[32]),
        'precision': _precision(raw_price),
        'quoteTime': quote_time,
        'quoteDate': quote_time[:10],
    }


def _fetch_tencent_quotes():
    resp = requests.get(
        TENCENT_URL + ','.join(TENCENT_CODES),
        timeout=REQUEST_TIMEOUT,
        headers={'Referer': 'https://gu.qq.com/'},
    )
    resp.raise_for_status()
    text = resp.content.decode('gbk', errors='ignore')
    quotes = {}
    for line in text.split(';'):
        line = line.strip()
        if '=' not in line:
            continue
        var_name, raw_value = line.split('=', 1)
        code = var_name.strip().removeprefix('v_')
        parsed = _parse_tencent_quote(raw_value.strip().strip('"'))
        if parsed:
            quotes[code] = parsed
    return quotes


def _fetch_sina_cnh():
    resp = requests.get(
        SINA_URL,
        timeout=REQUEST_TIMEOUT,
        headers={'Referer': 'https://finance.sina.com.cn/'},
    )
    resp.raise_for_status()
    text = resp.content.decode('gbk', errors='ignore')
    if '="' not in text:
        raise ValueError('新浪行情格式异常')
    raw = text.split('="', 1)[1].rsplit('"', 1)[0]
    fields = raw.split(',')
    if len(fields) < 18:
        raise ValueError('新浪行情字段不足')
    raw_price = fields[8].strip()
    quote_date = fields[17].strip()
    return {
        'price': _to_float(raw_price),
        'change': _to_float(fields[11]),
        'changePercent': _to_float(fields[10]),
        'precision': _precision(raw_price),
        'quoteTime': f'{quote_date} {fields[0].strip()}'.strip(),
        'quoteDate': quote_date,
    }


def _fetch_cfets_middle_price():
    resp = requests.get(CFETS_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = json.loads(resp.content.decode('utf-8-sig'))
    last_date = payload.get('data', {}).get('lastDate', '')
    for record in payload.get('records', []):
        if record.get('vrtEName') == 'USD/CNY':
            raw_price = str(record.get('price', '')).strip()
            return {
                'price': _to_float(raw_price),
                'change': None,
                'changePercent': None,
                'precision': _precision(raw_price),
                'quoteTime': _format_cfets_time(last_date),
                'quoteDate': last_date[:10],
            }
    raise ValueError('未找到人民币中间价')


def _market_status_cn(now):
    if now.weekday() >= 5:
        return 'holiday'
    current = now.time()
    if time(9, 30) <= current < time(11, 30):
        return 'open'
    if time(11, 30) <= current < time(13, 0):
        return 'break'
    if time(13, 0) <= current < time(15, 0):
        return 'open'
    return 'closed'


def _market_status_us(now):
    if now.weekday() >= 5:
        return 'holiday'
    return 'open' if time(9, 30) <= now.time() < time(16, 0) else 'closed'


def _market_status_commodity(now):
    weekday, current = now.weekday(), now.time()
    if weekday == 5:
        return 'open' if current < time(5, 0) else 'holiday'
    if weekday == 6:
        return 'holiday'
    if weekday == 0 and current < time(6, 0):
        return 'holiday'
    if time(5, 0) <= current < time(6, 0):
        return 'closed'
    return 'open'


def _apply_holiday(status, quote_date, local_date):
    if status in ('open', 'break') and quote_date and quote_date != local_date.isoformat():
        return 'holiday'
    return status


def _build_item(code, name, quotes):
    quote = quotes.get(code) or {}
    return {
        'key': code,
        'name': name,
        'price': quote.get('price'),
        'change': quote.get('change'),
        'changePercent': quote.get('changePercent'),
        'precision': quote.get('precision', 2),
        'quoteTime': quote.get('quoteTime', ''),
    }


def _build_group(key, name, status, items):
    return {
        'key': key,
        'name': name,
        'status': status,
        'statusText': STATUS_TEXT.get(status, '休市'),
        'items': items,
    }


def _build_overview():
    now_cn = datetime.now(CN_TZ)
    now_us = datetime.now(US_TZ)

    tencent_quotes, cnh_quote, middle_price = {}, None, None
    failed_fetches = 0

    try:
        tencent_quotes = _fetch_tencent_quotes()
    except Exception:
        failed_fetches += 1
    try:
        cnh_quote = _fetch_sina_cnh()
    except Exception:
        failed_fetches += 1
    try:
        middle_price = _fetch_cfets_middle_price()
    except Exception:
        failed_fetches += 1

    if failed_fetches == 3:
        raise RuntimeError('行情数据获取失败')

    cn_status = _apply_holiday(
        _market_status_cn(now_cn),
        (tencent_quotes.get('sh000300') or {}).get('quoteDate'),
        now_cn.date(),
    )
    us_status = _apply_holiday(
        _market_status_us(now_us),
        (tencent_quotes.get('usINX') or {}).get('quoteDate'),
        now_us.date(),
    )
    commodity_status = _market_status_commodity(now_cn)

    fx_items = [_build_item('fx_susdcnh', 'USD/CNH 离岸人民币', {'fx_susdcnh': cnh_quote} if cnh_quote else {})]
    if middle_price:
        fx_items.append({
            'key': 'usdcny_ccpr',
            'name': '人民币中间价',
            'price': middle_price['price'],
            'change': None,
            'changePercent': None,
            'precision': middle_price['precision'],
            'quoteTime': middle_price['quoteTime'],
            'quoteDate': middle_price['quoteDate'],
        })
    else:
        fx_items.append(_build_item('usdcny_ccpr', '人民币中间价', {}))

    return {
        'updateTime': now_cn.strftime('%Y-%m-%d %H:%M:%S'),
        'stale': False,
        'groups': [
            _build_group(
                'cn', 'A股指数', cn_status,
                [_build_item(code, name, tencent_quotes) for code, name in CN_ITEMS],
            ),
            _build_group(
                'us', '美股指数', us_status,
                [_build_item(code, name, tencent_quotes) for code, name in US_ITEMS],
            ),
            _build_group(
                'commodity', '贵金属 / 原油', commodity_status,
                [_build_item(code, name, tencent_quotes) for code, name in COMMODITY_ITEMS],
            ),
            _build_group('fx', '外汇', commodity_status, fx_items),
        ],
    }


def get_market_overview_data(force=False):
    if not force:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached
    try:
        overview = _build_overview()
        cache.set(CACHE_KEY, overview, CACHE_TTL)
        cache.set(STALE_CACHE_KEY, overview, STALE_CACHE_TTL)
        return overview
    except Exception:
        stale = cache.get(STALE_CACHE_KEY)
        if stale:
            stale['stale'] = True
            return stale
        raise
