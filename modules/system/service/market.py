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

EASTMONEY_QUOTE_URL = 'https://push2.eastmoney.com/api/qt/stock/get'
EASTMONEY_TREND_URL = 'https://push2his.eastmoney.com/api/qt/stock/trends2/get'
EASTMONEY_KLINE_URL = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
EASTMONEY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
}

TREND_SECID_MAP = {
    'sh000001': '1.000001',
    'sh000300': '1.000300',
    'sz399006': '0.399006',
    'sh000688': '1.000688',
    'usINX': '100.SPX',
    'usNDX': '100.NDX100',
    'usd_index': '100.UDI',
    'hf_XAU': '122.XAU',
    'hf_XAG': '122.XAG',
    'hf_OIL': '112.B00Y',
    'hf_CL': '102.CL00Y',
}
TREND_PERIODS = ('minute', 'day', 'week', 'month')
TREND_CACHE_TTL = {'minute': 30, 'day': 300, 'week': 300, 'month': 600}
TREND_KLINE_LIMIT = 120

CN_ITEMS = [
    ('sh000001', '上证指数'),
    ('sh000300', '沪深300'),
    ('sz399006', '创业板指'),
    ('sh000688', '科创50'),
]
US_ITEMS = [('usINX', '标普500'), ('usNDX', '纳斯达克100')]
COMMODITY_ITEMS = [
    ('hf_XAU', '伦敦金'),
    ('hf_XAG', '伦敦银'),
    ('hf_OIL', '布伦特原油'),
    ('hf_CL', 'NYMEX原油'),
]
# 国内金价由伦敦金（美元/盎司）按离岸人民币汇率折算（元/克）
TROY_OUNCE_GRAMS = 31.1035
# 美元指数走东方财富（腾讯无该品种），key 与趋势弹窗保持一致
USD_INDEX_ITEM = ('usd_index', '美元指数', '100.UDI')
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


def _fetch_eastmoney_quote(secid):
    data = _request_eastmoney_data(EASTMONEY_QUOTE_URL, {
        'secid': secid,
        'fields': 'f43,f57,f58,f59,f60,f86,f169,f170',
    })
    precision = int(data.get('f59') or 2)
    scale = 10 ** precision
    price = _to_float(data.get('f43'))
    change = _to_float(data.get('f169'))
    percent = _to_float(data.get('f170'))
    quote_time = ''
    timestamp = data.get('f86')
    if timestamp:
        quote_time = datetime.fromtimestamp(int(timestamp), CN_TZ).strftime('%Y-%m-%d %H:%M:%S')
    return {
        'price': round(price / scale, precision) if price is not None else None,
        'change': round(change / scale, precision) if change is not None else None,
        'changePercent': round(percent / 100, 2) if percent is not None else None,
        'precision': precision,
        'quoteTime': quote_time,
        'quoteDate': quote_time[:10],
    }


def _build_gold_cny_item(xau_quote, cnh_quote):
    xau_quote = xau_quote or {}
    cnh_quote = cnh_quote or {}
    xau_price, xau_change = xau_quote.get('price'), xau_quote.get('change')
    cnh_price, cnh_change = cnh_quote.get('price'), cnh_quote.get('change')
    quote = {}
    if None not in (xau_price, xau_change, cnh_price, cnh_change):
        prev = (xau_price - xau_change) * (cnh_price - cnh_change) / TROY_OUNCE_GRAMS
        price = xau_price * cnh_price / TROY_OUNCE_GRAMS
        if prev:
            quote = {
                'price': round(price, 2),
                'change': round(price - prev, 2),
                'changePercent': round((price - prev) / prev * 100, 2),
                'precision': 2,
                'quoteTime': xau_quote.get('quoteTime', ''),
            }
    return _build_item('xau_cny', '国内金价（折算）', {'xau_cny': quote} if quote else {})


def _build_overview():
    now_cn = datetime.now(CN_TZ)
    now_us = datetime.now(US_TZ)

    tencent_quotes, cnh_quote, middle_price, usd_index_quote = {}, None, None, None
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
    try:
        usd_index_quote = _fetch_eastmoney_quote(USD_INDEX_ITEM[2])
    except Exception:
        pass

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
    fx_items.append(
        _build_item(
            USD_INDEX_ITEM[0],
            USD_INDEX_ITEM[1],
            {USD_INDEX_ITEM[0]: usd_index_quote} if usd_index_quote else {},
        )
    )

    commodity_items = []
    for code, name in COMMODITY_ITEMS:
        commodity_items.append(_build_item(code, name, tencent_quotes))
        if code == 'hf_XAU':
            commodity_items.append(
                _build_gold_cny_item(
                    tencent_quotes.get('hf_XAU'),
                    cnh_quote,
                )
            )

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
                commodity_items,
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


def _request_eastmoney_data(url, params):
    resp = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
        headers=EASTMONEY_HEADERS,
    )
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get('data')
    if not data:
        raise ValueError('东方财富行情数据为空')
    return data


def _fetch_trend_minute(secid):
    data = _request_eastmoney_data(EASTMONEY_TREND_URL, {
        'secid': secid,
        'ndays': 1,
        'iscr': 0,
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
    })
    points = []
    for line in data.get('trends') or []:
        fields = line.split(',')
        if len(fields) < 8:
            continue
        points.append({
            'time': fields[0],
            'price': _to_float(fields[2]),
            'avg': _to_float(fields[7]),
            'volume': _to_float(fields[5]),
        })
    return {
        'name': data.get('name', ''),
        'precision': data.get('decimal', 2),
        'preClose': _to_float(data.get('preClose')),
        'points': points,
    }


KLINE_KLT_MAP = {'day': 101, 'week': 102, 'month': 103}


def _fetch_trend_kline(secid, period):
    data = _request_eastmoney_data(EASTMONEY_KLINE_URL, {
        'secid': secid,
        'klt': KLINE_KLT_MAP[period],
        'fqt': 1,
        'lmt': TREND_KLINE_LIMIT,
        'end': '20500101',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
    })
    items = []
    for line in data.get('klines') or []:
        fields = line.split(',')
        if len(fields) < 6:
            continue
        items.append({
            'date': fields[0],
            'open': _to_float(fields[1]),
            'close': _to_float(fields[2]),
            'high': _to_float(fields[3]),
            'low': _to_float(fields[4]),
            'volume': _to_float(fields[5]),
        })
    return {
        'name': data.get('name', ''),
        'precision': data.get('decimal', 2),
        'items': items,
    }


def get_market_trend_data(key, period='minute', force=False):
    if key not in TREND_SECID_MAP:
        raise KeyError('该行情暂不支持趋势查看')
    if period not in TREND_PERIODS:
        raise ValueError('不支持的周期')
    cache_key = f'market:trend:{key}:{period}'
    if not force:
        cached = cache.get(cache_key)
        if cached:
            return cached
    secid = TREND_SECID_MAP[key]
    if period == 'minute':
        trend = _fetch_trend_minute(secid)
    else:
        trend = _fetch_trend_kline(secid, period)
    result = {'key': key, 'period': period, **trend}
    cache.set(cache_key, result, TREND_CACHE_TTL[period])
    return result
