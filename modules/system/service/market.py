import json
import logging
import time as time_module
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = 'market:overview'
STALE_CACHE_KEY = 'market:overview:stale'
CACHE_TTL = 30
STALE_CACHE_TTL = 600
REQUEST_TIMEOUT = 5
# 东方财富偶发返回空数据或被限流，失败时重试两轮
EASTMONEY_RETRY_ATTEMPTS = 3
EASTMONEY_RETRY_DELAY = 0.25
# 单条行情最近一次成功的值，用于上游短时失败时兜底（最长使用 1 小时）
LAST_QUOTE_CACHE_KEY = 'market:last_quotes'
LAST_QUOTE_MAX_AGE = 3600
LAST_QUOTE_CACHE_TTL = 86400
# 趋势数据最近一次成功的值，上游失败时降级展示
TREND_STALE_CACHE_TTL = 86400

CN_TZ = ZoneInfo('Asia/Shanghai')
US_TZ = ZoneInfo('America/New_York')
KOREA_TZ = ZoneInfo('Asia/Seoul')
JAPAN_TZ = ZoneInfo('Asia/Tokyo')
TAIPEI_TZ = ZoneInfo('Asia/Taipei')
HONG_KONG_TZ = ZoneInfo('Asia/Hong_Kong')

TENCENT_URL = 'https://qt.gtimg.cn/q='
SINA_URL = 'https://hq.sinajs.cn/list='
CFETS_URL = 'https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/fx/ccpr.json'

EASTMONEY_QUOTE_URL = 'https://push2.eastmoney.com/api/qt/stock/get'
EASTMONEY_ULIST_URL = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
EASTMONEY_TREND_URL = 'https://push2his.eastmoney.com/api/qt/stock/trends2/get'
EASTMONEY_KLINE_URL = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
EASTMONEY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://quote.eastmoney.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

TREND_SECID_MAP = {
    'sh000001': '1.000001',
    'sh000300': '1.000300',
    'sz399006': '0.399006',
    'sh000688': '1.000688',
    'kr_kospi': '100.KS11',
    'jp_n225': '100.N225',
    'tw_twii': '100.TWII',
    'hk_hsi': '100.HSI',
    'hk_hstech': '124.HSTECH',
    'usINX': '100.SPX',
    'usNDX': '100.NDX100',
    'usDJI': '100.DJIA',
    'usIXIC': '100.NDX',
    'usd_index': '100.UDI',
    'hf_XAU': '122.XAU',
    'hf_XAG': '122.XAG',
    'hf_OIL': '112.B00Y',
    'hf_CL': '102.CL00Y',
}
TREND_PERIODS = ('minute', 'hour', 'day', 'week', 'month')
TREND_CACHE_TTL = {'minute': 30, 'hour': 120, 'day': 300, 'week': 300, 'month': 600}
TREND_KLINE_LIMIT = 120

CN_ITEMS = [
    ('sh000001', '上证指数'),
    ('sh000300', '沪深300'),
    ('sz399006', '创业板指'),
    ('sh000688', '科创50'),
]
US_ITEMS = [
    ('usINX', '标普500'),
    ('usNDX', '纳斯达克100'),
    ('usDJI', '道琼斯'),
    ('usIXIC', '纳斯达克综合'),
]
COMMODITY_ITEMS = [
    ('hf_XAU', '伦敦金'),
    ('hf_XAG', '伦敦银'),
    ('hf_OIL', '布伦特原油'),
    ('hf_CL', 'NYMEX原油'),
]
# 上海黄金交易所 Au9999；key 保持稳定，避免自选失效
SGE_GOLD_KEY = 'sge_gold'
SGE_GOLD_NAME = 'Au9999'
SGE_GOLD_SECID = '118.AU9999'
# 美股指数期货走新浪（腾讯仅有标普500期货）
US_FUTURES_ITEMS = [
    ('hf_NQ', '纳斯达克100期货'),
    ('hf_ES', '标普500期货'),
    ('hf_YM', '道琼斯期货'),
]
# 港股指数走东方财富（腾讯无这些品种）
HK_ITEMS = [
    ('hk_hsi', '恒生指数', '100.HSI'),
    ('hk_hstech', '恒生科技指数', '124.HSTECH'),
]
# 亚太指数走东方财富（腾讯无这些品种）
ASIA_ITEMS = [
    ('kr_kospi', '韩国KOSPI', '100.KS11'),
    ('jp_n225', '日经225', '100.N225'),
    ('tw_twii', '台湾加权', '100.TWII'),
]
# 加密货币走新浪（美元计价，7×24 小时交易）
CRYPTO_ITEMS = [
    ('btc_btcbtcusd', '比特币', 'BTC/USD'),
    ('btc_btcethusd', '以太坊', 'ETH/USD'),
    ('btc_btcbnbusd', '币安币', 'BNB/USD'),
    ('btc_btcsolusd', 'Solana', 'SOL/USD'),
    ('btc_btcxrpusd', '瑞波币', 'XRP/USD'),
    ('btc_btcadausd', '艾达币', 'ADA/USD'),
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

ITEM_SYMBOLS = {
    'sh000001': 'SSE Composite',
    'sh000300': 'CSI 300',
    'sz399006': 'ChiNext',
    'sh000688': 'STAR 50',
    'kr_kospi': 'KOSPI',
    'jp_n225': 'Nikkei 225',
    'tw_twii': 'TAIEX',
    'hk_hsi': 'HSI',
    'hk_hstech': 'HSTECH',
    'hf_NQ': 'NQ',
    'hf_ES': 'ES',
    'hf_YM': 'YM',
    'usINX': 'S&P 500',
    'usNDX': 'Nasdaq 100',
    'usDJI': 'Dow Jones',
    'usIXIC': 'Nasdaq Composite',
    'hf_XAU': 'XAUUSD',
    'xau_cny': 'XAU/CNY',
    'hf_XAG': 'XAGUSD',
    'hf_OIL': 'Brent',
    'hf_CL': 'WTI',
    'fx_susdcnh': 'USD/CNH',
    'usdcny_ccpr': 'USD/CNY',
    'usd_index': 'DXY',
    'sge_gold': 'AU9999',
    'btc_btcbtcusd': 'BTC/USD',
    'btc_btcethusd': 'ETH/USD',
    'btc_btcbnbusd': 'BNB/USD',
    'btc_btcsolusd': 'SOL/USD',
    'btc_btcxrpusd': 'XRP/USD',
    'btc_btcadausd': 'ADA/USD',
}

# 需要从东方财富取价的条目：港股、亚太、美元指数、上金所黄金
EASTMONEY_QUOTE_ITEMS = (
    HK_ITEMS
    + ASIA_ITEMS
    + [
        (USD_INDEX_ITEM[0], USD_INDEX_ITEM[1], USD_INDEX_ITEM[2]),
        (SGE_GOLD_KEY, SGE_GOLD_NAME, SGE_GOLD_SECID),
    ]
)
EASTMONEY_QUOTE_SECIDS = [secid for _key, _name, secid in EASTMONEY_QUOTE_ITEMS]

# 东方财富失败时的备用源（腾讯 / 新浪）
TENCENT_HK_CODES = {'hk_hsi': 'hkHSI', 'hk_hstech': 'hkHSTECH'}
SINA_FALLBACK_CODES = {
    'kr_kospi': 'b_KOSPI',
    'jp_n225': 'b_NKY',
    'usd_index': 'DINIW',
    'sge_gold': 'SGE_AU9999',
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
    # 腾讯港股等品种返回 2026/11/13 11:59:59，统一为 ISO 日期，供休市判断使用
    return raw.replace('/', '-')


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
        change_percent = _to_float(fields[1])
        if price is not None and prev_close not in (None, 0):
            change = round(price - prev_close, precision)
            # 新浪外盘期货不返回涨跌幅，按昨收自行计算
            if change_percent is None:
                change_percent = round(change / prev_close * 100, 2)
        quote_date = fields[12].strip()
        return {
            'price': price,
            'change': change,
            'changePercent': change_percent,
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


def _parse_sina_crypto_quote(raw):
    # 新浪加密行情字段：0 时间、3 最新价、6 最高、7 最低、8 今开、11 日期
    fields = raw.split(',')
    if len(fields) < 12:
        return None
    raw_price = fields[3].strip()
    price = _to_float(raw_price)
    open_price = _to_float(fields[8])
    # 新浪固定返回 4 位小数，高价币按 2 位展示更符合习惯
    precision = 2 if price is not None and price >= 100 else _precision(raw_price)
    change = None
    change_percent = None
    if price is not None and open_price not in (None, 0):
        change = round(price - open_price, precision)
        change_percent = round(change / open_price * 100, 2)
    quote_date = fields[11].strip()
    return {
        'price': price,
        'change': change,
        'changePercent': change_percent,
        'precision': precision,
        'quoteTime': f'{quote_date} {fields[0].strip()}'.strip(),
        'quoteDate': quote_date,
    }


def _parse_sina_global_index_quote(raw):
    # 新浪国际指数：0 名称、1 最新价、2 涨跌额、3 涨跌幅、5 当地时间、6 日期
    fields = raw.split(',')
    if len(fields) < 7:
        return None
    raw_price = fields[1].strip()
    price = _to_float(raw_price)
    if price is None:
        return None
    quote_date = fields[6].strip()
    return {
        'price': price,
        'change': _to_float(fields[2]),
        'changePercent': _to_float(fields[3]),
        'precision': _precision(raw_price),
        'quoteTime': f'{quote_date} {fields[5].strip()}'.strip(),
        'quoteDate': quote_date,
    }


def _parse_sina_usd_index_quote(raw):
    # 新浪美元指数：0 时间、1 最新价、5 昨收、6 最高、7 最低、10 日期
    fields = raw.split(',')
    if len(fields) < 11:
        return None
    raw_price = fields[1].strip()
    price = _to_float(raw_price)
    if price is None:
        return None
    prev_close = _to_float(fields[5])
    precision = _precision(raw_price)
    change = None
    change_percent = None
    if prev_close not in (None, 0):
        change = round(price - prev_close, precision)
        change_percent = round(change / prev_close * 100, 2)
    quote_date = fields[10].strip()
    return {
        'price': price,
        'change': change,
        'changePercent': change_percent,
        'precision': precision,
        'quoteTime': f'{quote_date} {fields[0].strip()}'.strip(),
        'quoteDate': quote_date,
    }


def _parse_sina_sge_quote(raw):
    # 新浪上金所：3 最新价、5 昨收、16 行情时间、17 涨跌幅
    fields = raw.split(',')
    if len(fields) < 18:
        return None
    raw_price = fields[3].strip()
    price = _to_float(raw_price)
    if price is None:
        return None
    prev_close = _to_float(fields[5])
    precision = _precision(raw_price)
    change = None
    change_percent = _to_float(fields[17].strip().rstrip('%'))
    if prev_close not in (None, 0):
        change = round(price - prev_close, precision)
        if change_percent is None:
            change_percent = round(change / prev_close * 100, 2)
    quote_time = fields[16].strip().replace('/', '-')
    return {
        'price': price,
        'change': change,
        'changePercent': change_percent,
        'precision': precision,
        'quoteTime': quote_time,
        'quoteDate': quote_time[:10],
    }


SINA_FALLBACK_PARSERS = {
    'b_KOSPI': _parse_sina_global_index_quote,
    'b_NKY': _parse_sina_global_index_quote,
    'DINIW': _parse_sina_usd_index_quote,
    'SGE_AU9999': _parse_sina_sge_quote,
}


def _fetch_tencent_quotes(codes=None):
    resp = requests.get(
        TENCENT_URL + ','.join(codes or TENCENT_CODES),
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


def _fetch_sina_quotes(codes, parser=_parse_tencent_quote):
    resp = requests.get(
        SINA_URL + ','.join(codes),
        timeout=REQUEST_TIMEOUT,
        headers={'Referer': 'https://finance.sina.com.cn/'},
    )
    resp.raise_for_status()
    text = resp.content.decode('gbk', errors='ignore')
    quotes = {}
    for line in text.split(';'):
        line = line.strip()
        if '="' not in line:
            continue
        var_name, raw_value = line.split('=', 1)
        code = var_name.strip().removeprefix('var hq_str_')
        raw = raw_value.strip().strip('"')
        if not raw:
            continue
        parsed = parser(raw)
        if parsed:
            quotes[code] = parsed
    return quotes


def _fetch_sina_quotes_by_parser(parsers):
    """按 code 分别解析，供不同格式的备用行情一次请求获取。"""
    resp = requests.get(
        SINA_URL + ','.join(parsers.keys()),
        timeout=REQUEST_TIMEOUT,
        headers={'Referer': 'https://finance.sina.com.cn/'},
    )
    resp.raise_for_status()
    text = resp.content.decode('gbk', errors='ignore')
    quotes = {}
    for line in text.split(';'):
        line = line.strip()
        if '="' not in line:
            continue
        var_name, raw_value = line.split('=', 1)
        code = var_name.strip().removeprefix('var hq_str_')
        raw = raw_value.strip().strip('"')
        parser = parsers.get(code)
        if not raw or not parser:
            continue
        parsed = parser(raw)
        if parsed:
            quotes[code] = parsed
    return quotes


def _fetch_sina_cnh():
    resp = requests.get(
        SINA_URL + 'fx_susdcnh',
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


def _market_status_us_futures(now):
    """CME Globex：周日 18:00 至周五 17:00（美东），每日 17:00-18:00 休市。"""
    weekday, current = now.weekday(), now.time()
    if weekday == 5:
        return 'holiday'
    if weekday == 6:
        return 'open' if current >= time(18, 0) else 'holiday'
    if weekday == 4:
        return 'open' if current < time(17, 0) else 'holiday'
    if time(17, 0) <= current < time(18, 0):
        return 'closed'
    return 'open'


# 亚太各市场交易时段（当地时间）
ASIA_SESSIONS = [
    (KOREA_TZ, [(time(9, 0), time(15, 30))]),
    (JAPAN_TZ, [(time(9, 0), time(11, 30)), (time(12, 30), time(15, 30))]),
    (TAIPEI_TZ, [(time(9, 0), time(13, 30))]),
]


def _market_status_hk(now):
    local = now.astimezone(HONG_KONG_TZ)
    if local.weekday() >= 5:
        return 'holiday'
    current = local.time()
    if time(9, 30) <= current < time(12, 0) or time(13, 0) <= current < time(16, 0):
        return 'open'
    if time(12, 0) <= current < time(13, 0):
        return 'break'
    return 'closed'


def _market_status_asia(now):
    statuses = []
    for tz, sessions in ASIA_SESSIONS:
        local = now.astimezone(tz)
        if local.weekday() >= 5:
            statuses.append('holiday')
        elif any(start <= local.time() < end for start, end in sessions):
            statuses.append('open')
        else:
            statuses.append('closed')
    if all(status == 'holiday' for status in statuses):
        return 'holiday'
    return 'open' if 'open' in statuses else 'closed'


def _apply_holiday(status, quote_date, local_date):
    if status in ('open', 'break') and quote_date and quote_date != local_date.isoformat():
        return 'holiday'
    return status


def _build_item(code, name, quotes):
    quote = quotes.get(code) or {}
    return {
        'key': code,
        'name': name,
        'symbol': ITEM_SYMBOLS.get(code, ''),
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
    # 批量接口已重试过，逐条补齐时不再重复重试，避免接口整体变慢
    data = _request_eastmoney_data(EASTMONEY_QUOTE_URL, {
        'secid': secid,
        'fields': 'f43,f57,f58,f59,f60,f86,f169,f170',
    }, attempts=1)
    precision = int(data.get('f59') or 2)
    scale = 10 ** precision
    price = _to_float(data.get('f43'))
    if price is None:
        raise ValueError('东方财富未返回有效价格')
    change = _to_float(data.get('f169'))
    percent = _to_float(data.get('f170'))
    quote_time = ''
    timestamp = data.get('f86')
    if timestamp:
        quote_time = datetime.fromtimestamp(int(timestamp), CN_TZ).strftime('%Y-%m-%d %H:%M:%S')
    return {
        'price': round(price / scale, precision),
        'change': round(change / scale, precision) if change is not None else None,
        'changePercent': round(percent / 100, 2) if percent is not None else None,
        'precision': precision,
        'quoteTime': quote_time,
        'quoteDate': quote_time[:10],
    }


def _parse_eastmoney_batch_row(row):
    price = _to_float(row.get('f2'))
    if price is None:
        return None
    try:
        precision = int(row.get('f152'))
    except (TypeError, ValueError):
        precision = 2
    if precision <= 0:
        precision = 2
    quote_time = ''
    timestamp = row.get('f124')
    try:
        if timestamp:
            quote_time = datetime.fromtimestamp(int(timestamp), CN_TZ).strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError, OSError):
        quote_time = ''
    return {
        'price': price,
        'change': _to_float(row.get('f4')),
        'changePercent': _to_float(row.get('f3')),
        'precision': precision,
        'quoteTime': quote_time,
        'quoteDate': quote_time[:10],
    }


def _fetch_eastmoney_batch_quotes(secids):
    """一次请求拉取多个东财品种，减少请求数与单条失败概率。"""
    data = _request_eastmoney_data(EASTMONEY_ULIST_URL, {
        'fltt': 2,
        'invt': 2,
        'secids': ','.join(secids),
        'fields': 'f2,f3,f4,f12,f13,f14,f18,f124,f152',
    })
    quotes = {}
    for row in data.get('diff') or []:
        quote = _parse_eastmoney_batch_row(row)
        code, market = row.get('f12'), row.get('f13')
        if quote and code is not None and market is not None:
            quotes[f'{market}.{code}'] = quote
    return quotes


def _fill_fallback_quotes(quotes):
    """东财失败时改用腾讯 / 新浪备用源补齐。"""
    missing = [key for key, _name, _secid in EASTMONEY_QUOTE_ITEMS if key not in quotes]
    if not missing:
        return

    hk_missing = [(key, TENCENT_HK_CODES[key]) for key in missing if key in TENCENT_HK_CODES]
    if hk_missing:
        try:
            tencent_quotes = _fetch_tencent_quotes([code for _key, code in hk_missing])
        except Exception as exc:
            logger.warning('腾讯港股备用行情获取失败: %s', exc)
            tencent_quotes = {}
        for key, code in hk_missing:
            quote = tencent_quotes.get(code)
            if quote:
                # 腾讯返回 3 位小数，港股指数与东财保持一致按 2 位展示
                quote['precision'] = 2
                quotes[key] = quote
            else:
                logger.warning('备用源仍无港股行情: %s(%s)', key, code)

    sina_parsers = {}
    sina_key_map = {}
    for key in missing:
        code = SINA_FALLBACK_CODES.get(key)
        parser = SINA_FALLBACK_PARSERS.get(code) if code else None
        if code and parser:
            sina_parsers[code] = parser
            sina_key_map[code] = key
    if not sina_parsers:
        return
    try:
        sina_quotes = _fetch_sina_quotes_by_parser(sina_parsers)
    except Exception as exc:
        logger.warning('新浪备用行情获取失败: %s', exc)
        return
    for code, key in sina_key_map.items():
        quote = sina_quotes.get(code)
        if quote:
            quotes[key] = quote
        else:
            logger.warning('备用源仍无行情: %s(%s)', key, code)


def _fetch_eastmoney_quotes():
    quotes = {}
    batch_failed = False
    try:
        batch_quotes = _fetch_eastmoney_batch_quotes(EASTMONEY_QUOTE_SECIDS)
    except Exception as exc:
        logger.warning('东方财富批量行情获取失败: %s', exc)
        batch_quotes = {}
        batch_failed = True

    missing = []
    for key, _name, secid in EASTMONEY_QUOTE_ITEMS:
        quote = batch_quotes.get(secid)
        if quote:
            quotes[key] = quote
        else:
            missing.append((key, secid))

    # 批量都失败说明东财整体不可用，直接走备用源，避免逐条重试拖慢接口
    for key, secid in ([] if batch_failed else missing):
        try:
            quotes[key] = _fetch_eastmoney_quote(secid)
        except Exception as exc:
            logger.warning('东方财富单条行情获取失败 %s(%s): %s', key, secid, exc)

    _fill_fallback_quotes(quotes)
    return quotes


def _apply_last_quotes(groups):
    """空条目用最近一次成功的行情兜底，返回是否使用了旧数据。"""
    last_quotes = cache.get(LAST_QUOTE_CACHE_KEY) or {}
    now_ts = datetime.now(CN_TZ).timestamp()
    used_stale = False
    fresh = {}
    for group in groups:
        for item in group.get('items') or []:
            key = item.get('key')
            if not key:
                continue
            filled = False
            if item.get('price') is None:
                cached = last_quotes.get(key) or {}
                if cached and now_ts - cached.get('cachedAt', 0) <= LAST_QUOTE_MAX_AGE:
                    item.update({
                        'price': cached.get('price'),
                        'change': cached.get('change'),
                        'changePercent': cached.get('changePercent'),
                        'precision': cached.get('precision', item.get('precision', 2)),
                        'quoteTime': cached.get('quoteTime', ''),
                    })
                    used_stale = True
                    filled = True
            if not filled and item.get('price') is not None:
                fresh[key] = {
                    'price': item.get('price'),
                    'change': item.get('change'),
                    'changePercent': item.get('changePercent'),
                    'precision': item.get('precision', 2),
                    'quoteTime': item.get('quoteTime', ''),
                    'cachedAt': now_ts,
                }
    if fresh:
        cache.set(LAST_QUOTE_CACHE_KEY, {**last_quotes, **fresh}, LAST_QUOTE_CACHE_TTL)
    return used_stale


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

    tencent_quotes, cnh_quote, middle_price = {}, None, None
    futures_quotes, crypto_quotes = {}, {}
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
        futures_quotes = _fetch_sina_quotes([code for code, _ in US_FUTURES_ITEMS])
    except Exception:
        pass
    try:
        crypto_quotes = _fetch_sina_quotes(
            [code for code, _, _ in CRYPTO_ITEMS],
            _parse_sina_crypto_quote,
        )
    except Exception:
        pass

    eastmoney_quotes = _fetch_eastmoney_quotes()

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
    hk_status = _apply_holiday(
        _market_status_hk(now_cn),
        (eastmoney_quotes.get('hk_hsi') or {}).get('quoteDate'),
        datetime.now(HONG_KONG_TZ).date(),
    )
    asia_status = _market_status_asia(now_cn)
    futures_status = _market_status_us_futures(now_us)

    fx_items = [
        _build_item('fx_susdcnh', '离岸人民币', {'fx_susdcnh': cnh_quote} if cnh_quote else {}),
        _build_gold_cny_item(tencent_quotes.get('hf_XAU'), cnh_quote),
    ]
    if middle_price:
        fx_items.append({
            'key': 'usdcny_ccpr',
            'name': '人民币中间价',
            'symbol': ITEM_SYMBOLS.get('usdcny_ccpr', ''),
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
            {USD_INDEX_ITEM[0]: eastmoney_quotes.get(USD_INDEX_ITEM[0])}
            if eastmoney_quotes.get(USD_INDEX_ITEM[0]) else {},
        )
    )

    commodity_items = []
    for code, name in COMMODITY_ITEMS:
        commodity_items.append(_build_item(code, name, tencent_quotes))
        if code == 'hf_XAG':
            commodity_items.append(
                _build_item(
                    SGE_GOLD_KEY,
                    SGE_GOLD_NAME,
                    {SGE_GOLD_KEY: eastmoney_quotes.get(SGE_GOLD_KEY)}
                    if eastmoney_quotes.get(SGE_GOLD_KEY) else {},
                )
            )

    groups = [
        _build_group(
            'cn', 'A股指数', cn_status,
            [_build_item(code, name, tencent_quotes) for code, name in CN_ITEMS],
        ),
        _build_group(
            'hk', '港股指数', hk_status,
            [_build_item(code, name, eastmoney_quotes) for code, name, _ in HK_ITEMS],
        ),
        _build_group(
            'asia', '亚太市场', asia_status,
            [_build_item(code, name, eastmoney_quotes) for code, name, _ in ASIA_ITEMS],
        ),
        _build_group(
            'us', '美股指数', us_status,
            [_build_item(code, name, tencent_quotes) for code, name in US_ITEMS],
        ),
        _build_group(
            'us_futures', '美股指数期货', futures_status,
            [_build_item(code, name, futures_quotes) for code, name in US_FUTURES_ITEMS],
        ),
        _build_group(
            'commodity', '贵金属 / 原油', commodity_status,
            commodity_items,
        ),
        _build_group('fx', '外汇', commodity_status, fx_items),
        _build_group(
            'crypto', '加密货币', 'open',
            [_build_item(code, name, crypto_quotes) for code, name, _ in CRYPTO_ITEMS],
        ),
    ]
    used_stale = _apply_last_quotes(groups)

    return {
        'updateTime': now_cn.strftime('%Y-%m-%d %H:%M:%S'),
        'stale': used_stale,
        'groups': groups,
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


def _request_eastmoney_data(url, params, attempts=EASTMONEY_RETRY_ATTEMPTS):
    last_error = None
    for attempt in range(attempts):
        try:
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
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time_module.sleep(EASTMONEY_RETRY_DELAY)
    raise last_error


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


KLINE_KLT_MAP = {'hour': 60, 'day': 101, 'week': 102, 'month': 103}


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
    stale_cache_key = f'market:trend:last:{key}:{period}'
    if not force:
        cached = cache.get(cache_key)
        if cached:
            return cached
    secid = TREND_SECID_MAP[key]
    try:
        if period == 'minute':
            trend = _fetch_trend_minute(secid)
        else:
            trend = _fetch_trend_kline(secid, period)
    except Exception as exc:
        logger.warning('趋势数据获取失败 %s(%s): %s', key, period, exc)
        stale = cache.get(stale_cache_key)
        if stale:
            return {**stale, 'stale': True}
        raise
    result = {'key': key, 'period': period, **trend}
    cache.set(cache_key, result, TREND_CACHE_TTL[period])
    cache.set(stale_cache_key, result, TREND_STALE_CACHE_TTL)
    return result
